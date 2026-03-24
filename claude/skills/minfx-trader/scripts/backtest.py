#!/usr/bin/env python3
"""
みんなのFX WebTrader データを使ったバックテストスクリプト。

戦略: RSI(順張り) + MACD(0ライン超GC) + BB シグナル複数一致でエントリー
      スイングロー基準SL / RR×SL幅 TP / 建値移動トレーリング

使用方法:
  python backtest.py                          # MXNJPY 1h足
  python backtest.py --adx-filter             # ADXフィルター
  python backtest.py --ema-filter             # EMA200フィルター（上位足トレンド代替）
  python backtest.py --adx-filter --ema-filter --swing-sl --breakeven  # フル改善版
  python backtest.py --spread 2.0             # スプレッド込みテスト（pips）
  python backtest.py --surface surface:57     # サーフェス指定
"""
import subprocess
import json
import argparse
from datetime import datetime, timezone, timedelta

try:
    import pandas as pd
    import pandas_ta as ta
except ImportError as e:
    print(f"依存ライブラリ不足: pip install pandas pandas-ta\n{e}")
    import sys; sys.exit(1)

SURFACE  = "surface:56"
INTERVAL_TYPE = {"1m":1,"5m":2,"10m":3,"15m":4,"30m":5,"1h":6,"60m":6,"2h":7}
SYMBOL_IDS = {"MXNJPY":21,"USDJPY":1,"EURJPY":2,"GBPJPY":3}
JST = timezone(timedelta(hours=9))

# 実測値: 1pip / 1lot ≈ 101.5円
PIP_VALUE_PER_LOT = 101.5
LOT_SIZE = 1


def run_eval(surface: str, script: str) -> str:
    r = subprocess.run(["cmux","browser",surface,"eval",script],
                       capture_output=True, text=True, timeout=20)
    return r.stdout.strip()


def fetch_data(surface: str, symbol_id: int, chart_type: int, bars: int, swing_window: int = 10) -> pd.DataFrame:
    script = f"""
(function() {{
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/express/rest/pricing/chart/charts?symbolId={symbol_id}&chartType={chart_type}&side=-1&limit={bars}', false);
  xhr.send();
  return xhr.responseText;
}})();
"""
    raw = run_eval(surface, script)
    data = json.loads(raw).get("data", [])
    rows = []
    for item in data:
        dt = datetime.fromtimestamp(int(item[0]) / 1000, tz=JST)
        rows.append({"time": dt, "open": float(item[1]), "high": float(item[2]),
                     "low": float(item[3]), "close": float(item[4])})
    rows.sort(key=lambda r: r["time"])
    df = pd.DataFrame(rows).set_index("time")

    df["sma50"]  = ta.sma(df["close"], length=50)
    df["ema200"] = ta.ema(df["close"], length=200)   # 上位足トレンド代替フィルター用
    df["rsi14"]  = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["macd"]  = macd.iloc[:, 0]
        df["macd_s"] = macd.iloc[:, 2]

    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None:
        df["bb_upper"] = bb.iloc[:, 0]
        df["bb_lower"] = bb.iloc[:, 2]

    df["atr14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # ADXトレンドフィルター用
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx is not None:
        df["adx"]  = adx.iloc[:, 0]   # ADX
        df["dmp"]  = adx.iloc[:, 1]   # +DI
        df["dmn"]  = adx.iloc[:, 2]   # -DI

    # スイングロー/ハイ SL用（直近swing_window本の高値・安値）
    df["swing_low"]  = df["low"].rolling(swing_window, min_periods=max(3, swing_window//2)).min().shift(1)
    df["swing_high"] = df["high"].rolling(swing_window, min_periods=max(3, swing_window//2)).max().shift(1)

    return df.dropna()


def get_signals(row, prev) -> list[str]:
    """シグナル生成。RSIは順張り（45→50回復）、MACDは0ライン超GCを優先。"""
    sigs = []

    # RSI: 売られすぎ/買われすぎ（元の逆張り条件、ADX等と組み合わせで順張り的に使う）
    rsi = row.get("rsi14")
    if pd.notna(rsi):
        if rsi < 30: sigs.append("BUY")
        elif rsi > 70: sigs.append("SELL")

    # MACD: GC/DC
    m, ms, pm, pms = row.get("macd"), row.get("macd_s"), prev.get("macd"), prev.get("macd_s")
    if all(pd.notna(x) for x in [m, ms, pm, pms]):
        if pm < pms and m > ms:
            sigs.append("BUY")
        elif pm > pms and m < ms:
            sigs.append("SELL")

    # BB: バンド突破
    c, bu, bl = row.get("close"), row.get("bb_upper"), row.get("bb_lower")
    if all(pd.notna(x) for x in [c, bu, bl]):
        if c > bu: sigs.append("SELL")
        elif c < bl: sigs.append("BUY")

    return sigs


def is_active_session(dt, active_hours: tuple) -> bool:
    """JST時間でアクティブセッション判定"""
    h = dt.hour
    start, end = active_hours
    if start <= end:
        return start <= h < end
    else:  # 日をまたぐ場合（例: 21〜翌3時）
        return h >= start or h < end


def backtest(df: pd.DataFrame, rr: float, min_signals: int, lot: int,
             trend_filter: bool, active_hours: tuple | None,
             side_filter: str | None = None,
             adx_filter: bool = False,
             ema_filter: bool = False,
             swing_sl: bool = False,
             breakeven: bool = False,
             spread_pips: float = 0.0,
             adx_threshold: float = 25.0) -> list:
    trades = []
    position = None

    for i in range(1, len(df)):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        dt   = df.index[i]

        # 既存ポジションの管理
        if position is not None:
            side = position["side"]
            sl   = position["sl"]
            tp   = position["tp"]
            entry = position["entry"]

            if side == "BUY":
                # 建値移動: 含み益が1Rに達したらSLを建値に移動
                if breakeven and not position.get("breakeven_done"):
                    one_r = entry - position["initial_sl"]
                    if row["high"] >= entry + one_r:
                        position["sl"] = entry
                        position["breakeven_done"] = True
                        sl = entry

                if row["low"] <= sl:
                    pnl = (sl - entry) * 1000 * PIP_VALUE_PER_LOT * lot
                    pnl -= spread_pips * PIP_VALUE_PER_LOT * lot  # スプレッドコスト
                    # 建値移動後の建値決済はBREAKEVENとしてWIN扱い
                    if position.get("breakeven_done") and abs(sl - entry) < 1e-8:
                        result = "WIN"
                    else:
                        result = "WIN" if pnl > 0 else "LOSS"
                    trades.append({"result": result, "pnl": pnl,
                                   "entry": entry, "exit": sl,
                                   "pips": (sl - entry) * 1000,
                                   "entry_time": position["entry_time"], "exit_time": dt})
                    position = None
                elif row["high"] >= tp:
                    pnl = (tp - entry) * 1000 * PIP_VALUE_PER_LOT * lot
                    pnl -= spread_pips * PIP_VALUE_PER_LOT * lot
                    trades.append({"result": "WIN", "pnl": pnl,
                                   "entry": entry, "exit": tp,
                                   "pips": (tp - entry) * 1000,
                                   "entry_time": position["entry_time"], "exit_time": dt})
                    position = None
            else:  # SELL
                if breakeven and not position.get("breakeven_done"):
                    one_r = position["initial_sl"] - entry
                    if row["low"] <= entry - one_r:
                        position["sl"] = entry
                        position["breakeven_done"] = True
                        sl = entry

                if row["high"] >= sl:
                    pnl = (entry - sl) * 1000 * PIP_VALUE_PER_LOT * lot
                    pnl -= spread_pips * PIP_VALUE_PER_LOT * lot
                    if position.get("breakeven_done") and abs(sl - entry) < 1e-8:
                        result = "WIN"
                    else:
                        result = "WIN" if pnl > 0 else "LOSS"
                    trades.append({"result": result, "pnl": pnl,
                                   "entry": entry, "exit": sl,
                                   "pips": (entry - sl) * 1000,
                                   "entry_time": position["entry_time"], "exit_time": dt})
                    position = None
                elif row["low"] <= tp:
                    pnl = (entry - tp) * 1000 * PIP_VALUE_PER_LOT * lot
                    pnl -= spread_pips * PIP_VALUE_PER_LOT * lot
                    trades.append({"result": "WIN", "pnl": pnl,
                                   "entry": entry, "exit": tp,
                                   "pips": (entry - tp) * 1000,
                                   "entry_time": position["entry_time"], "exit_time": dt})
                    position = None

        # エントリー判定
        if position is None:
            if active_hours and not is_active_session(dt, active_hours):
                continue

            sigs  = get_signals(row, prev)
            buys  = sigs.count("BUY")
            sells = sigs.count("SELL")
            atr   = row.get("atr14", 0)
            close = row["close"]
            sma50 = row.get("sma50")
            ema200 = row.get("ema200")
            adx_val = row.get("adx", float("nan"))
            dmp_val = row.get("dmp", float("nan"))
            dmn_val = row.get("dmn", float("nan"))

            if buys >= min_signals and buys > sells:
                if side_filter == "sell":
                    continue
                if trend_filter and pd.notna(sma50) and close < sma50:
                    continue
                if ema_filter and pd.notna(ema200) and close < ema200:
                    continue
                if adx_filter:
                    if not pd.notna(adx_val) or adx_val < adx_threshold:
                        continue
                    if pd.notna(dmp_val) and pd.notna(dmn_val) and dmp_val < dmn_val:
                        continue

                # SL: スイングロー基準 or ATR固定
                if swing_sl and pd.notna(row.get("swing_low")):
                    sl_candidate = row["swing_low"] - atr * 0.5
                    sl = sl_candidate if sl_candidate < close else (close - atr * 2)
                else:
                    sl = close - atr * 2
                sl_width = close - sl
                if sl_width <= 0:
                    continue
                tp = close + sl_width * rr
                position = {"side": "BUY", "entry": close, "sl": sl, "tp": tp,
                            "initial_sl": sl, "entry_time": dt, "atr": atr,
                            "breakeven_done": False}

            elif sells >= min_signals and sells > buys:
                if side_filter == "buy":
                    continue
                if trend_filter and pd.notna(sma50) and close > sma50:
                    continue
                if ema_filter and pd.notna(ema200) and close > ema200:
                    continue
                if adx_filter:
                    if not pd.notna(adx_val) or adx_val < 25:
                        continue
                    if pd.notna(dmp_val) and pd.notna(dmn_val) and dmp_val > dmn_val:
                        continue

                if swing_sl and pd.notna(row.get("swing_high")):
                    sl_candidate = row["swing_high"] + atr * 0.5
                    sl = sl_candidate if sl_candidate > close else (close + atr * 2)
                else:
                    sl = close + atr * 2
                sl_width = sl - close
                if sl_width <= 0:
                    continue
                tp = close - sl_width * rr
                position = {"side": "SELL", "entry": close, "sl": sl, "tp": tp,
                            "initial_sl": sl, "entry_time": dt, "atr": atr,
                            "breakeven_done": False}

    return trades


def analyze(trades: list[dict]) -> dict:
    if not trades:
        return {"error": "トレードなし"}

    wins  = [t for t in trades if t["result"] == "WIN"]
    loses = [t for t in trades if t["result"] == "LOSS"]

    total_pnl  = sum(t["pnl"] for t in trades)
    gross_win  = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in loses))
    win_rate   = len(wins) / len(trades) * 100
    pf         = gross_win / gross_loss if gross_loss > 0 else float("inf")
    avg_win    = gross_win / len(wins) if wins else 0
    avg_loss   = gross_loss / len(loses) if loses else 0

    equity = 0
    peak   = 0
    max_dd = 0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(loses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "gross_win": gross_win,
        "gross_loss": -gross_loss,
        "profit_factor": pf,
        "avg_win": avg_win,
        "avg_loss": -avg_loss,
        "max_drawdown": max_dd,
        "avg_pips_win":  sum(t["pips"] for t in wins) / len(wins) if wins else 0,
        "avg_pips_loss": sum(t["pips"] for t in loses) / len(loses) if loses else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pair",          nargs="?", default="MXNJPY")
    parser.add_argument("--interval",    default="1h")
    parser.add_argument("--bars",        type=int, default=2000)
    parser.add_argument("--rr",          type=float, default=1.5, help="リスクリワード比")
    parser.add_argument("--min-signals", type=int, default=2,     help="エントリー最低シグナル数")
    parser.add_argument("--lot",         type=int, default=LOT_SIZE)
    parser.add_argument("--side",        default=None, choices=["buy","sell"])
    parser.add_argument("--surface",     default=SURFACE)
    parser.add_argument("--trend-filter",  action="store_true", help="SMA50トレンドフィルター")
    parser.add_argument("--adx-filter",   action="store_true", help="ADXフィルター（ADX>25+DI方向）")
    parser.add_argument("--ema-filter",   action="store_true", help="EMA200フィルター（上位足トレンド代替）")
    parser.add_argument("--swing-sl",      action="store_true", help="スイングロー基準SL")
    parser.add_argument("--swing-window",  type=int, default=10, help="スイングSLの参照期間（本数）")
    parser.add_argument("--adx-threshold", type=float, default=25.0, help="ADXフィルター閾値（デフォルト25）")
    parser.add_argument("--breakeven",     action="store_true", help="1R到達で建値移動")
    parser.add_argument("--spread",       type=float, default=0.0, help="スプレッド（pips）例: 2.0")
    parser.add_argument("--session",     default=None, help="セッション時間(JST) 例: 8-20")
    parser.add_argument("--json",        action="store_true")
    args = parser.parse_args()

    pair = args.pair.upper()
    chart_type = INTERVAL_TYPE.get(args.interval)
    symbol_id  = SYMBOL_IDS.get(pair, 21)

    active_hours = None
    if args.session:
        start_h, end_h = map(int, args.session.split("-"))
        active_hours = (start_h, end_h)

    print(f"データ取得中: {pair} {args.interval}足 {args.bars}本...")
    df = fetch_data(args.surface, symbol_id, chart_type, args.bars, args.swing_window)
    period_from = df.index[0].strftime("%Y-%m-%d")
    period_to   = df.index[-1].strftime("%Y-%m-%d")

    filters = []
    if args.trend_filter: filters.append("SMA50")
    if args.adx_filter:   filters.append(f"ADX(>{args.adx_threshold:.0f}+DI)")
    if args.ema_filter:   filters.append("EMA200")
    if args.swing_sl:     filters.append("スイングロー-SL")
    if args.breakeven:    filters.append("建値移動")
    if args.spread > 0:   filters.append(f"スプレッド{args.spread}pips")
    if active_hours:      filters.append(f"時間帯({args.session}時JST)")
    filter_str = " + ".join(filters) if filters else "なし"
    print(f"期間: {period_from} 〜 {period_to}  ({len(df)}本)")
    print(f"フィルター: {filter_str}\n")

    trades = backtest(df, args.rr, args.min_signals, args.lot,
                      args.trend_filter, active_hours, args.side,
                      args.adx_filter, args.ema_filter,
                      args.swing_sl, args.breakeven, args.spread,
                      args.adx_threshold)
    stats = analyze(trades)

    if args.json:
        print(json.dumps({"stats": stats, "trades": [
            {**t, "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"])}
            for t in trades
        ]}, ensure_ascii=False, indent=2))
        return

    if "error" in stats:
        print(f"結果: {stats['error']}")
        return

    sl_mode = "スイングロー-0.5ATR" if args.swing_sl else "2×ATR"
    print(f"=== バックテスト結果 ===")
    print(f"戦略: {args.min_signals}シグナル以上 / RSI順張り+MACD0超GC+BB / SL={sl_mode} / TP={args.rr}×RR")
    print(f"─────────────────────────────")
    print(f"総トレード数:   {stats['total_trades']}回")
    print(f"勝率:           {stats['win_rate']:.1f}%  (勝:{stats['wins']} / 負:{stats['losses']})")
    print(f"プロフィットF:  {stats['profit_factor']:.2f}")
    print(f"純損益:         {stats['total_pnl']:+,.0f}円")
    print(f"総利益:         {stats['gross_win']:+,.0f}円")
    print(f"総損失:         {stats['gross_loss']:+,.0f}円")
    print(f"平均利益:       {stats['avg_win']:+,.0f}円  ({stats['avg_pips_win']:+.1f}pips)")
    print(f"平均損失:       {stats['avg_loss']:+,.0f}円  ({stats['avg_pips_loss']:+.1f}pips)")
    print(f"最大DD:         {stats['max_drawdown']:+,.0f}円")

    print(f"\n=== 直近10トレード ===")
    for t in trades[-10:]:
        icon = "✅" if t["result"] == "WIN" else "❌"
        print(f"{icon} {t['entry_time'].strftime('%m/%d %H:%M')}  {t['pips']:+.1f}pips  {t['pnl']:+,.0f}円")


if __name__ == "__main__":
    main()
