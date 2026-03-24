#!/usr/bin/env python3
"""
FXチャートデータ + テクニカル指標取得スクリプト
みんなのFX Webトレーダーから直接取得（リアルタイム・遅延なし）。
事前にcmux-browserでWebトレーダーを開いておく必要がある。

使用方法:
  python get_chart.py                        # MXNJPY 5分足 直近100本
  python get_chart.py USDJPY                 # 通貨ペア指定
  python get_chart.py MXNJPY --interval 1m  # 足種指定（1m/5m/10m/15m/30m/1h/2h）
  python get_chart.py MXNJPY --bars 200      # 本数指定
  python get_chart.py MXNJPY --json          # JSON出力（パイプ連携用）
  python get_chart.py MXNJPY --surface surface:57  # サーフェス指定
"""
import sys
import json
import subprocess
import argparse
from datetime import datetime, timezone, timedelta

try:
    import pandas as pd
    import pandas_ta as ta
except ImportError as e:
    print(f"依存ライブラリ不足: pip install pandas pandas-ta\n{e}")
    sys.exit(1)

SURFACE = "surface:34"

# 足種 → chartType マッピング（みんなのFX API）
INTERVAL_TYPE = {
    "1m":  1,
    "5m":  2,
    "10m": 3,
    "15m": 4,
    "30m": 5,
    "1h":  6,
    "60m": 6,
    "2h":  7,
}

# 通貨ペア名 → symbolId（みんなのFX、通常プラン）
SYMBOL_IDS = {
    "USDJPY":  1,
    "EURJPY":  2,
    "GBPJPY":  3,
    "AUDJPY":  4,
    "NZDJPY":  5,
    "CADJPY":  6,
    "CHFJPY":  7,
    "EURUSD":  8,
    "GBPUSD":  9,
    "AUDUSD": 10,
    "NZDUSD": 11,
    "USDCAD": 12,
    "USDCHF": 13,
    "MXNJPY": 21,
    "ZARJPY": 22,
    "TRYJPY": 23,
}


def run_eval(surface: str, script: str) -> str:
    result = subprocess.run(
        ["cmux", "browser", surface, "eval", script],
        capture_output=True, text=True, timeout=15
    )
    return result.stdout.strip()


def fetch_ohlc(surface: str, symbol_id: int, chart_type: int, bars: int) -> list[dict]:
    """みんなのFX WebTrader APIからOHLCデータを取得"""
    script = f"""
(function() {{
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/express/rest/pricing/chart/charts?symbolId={symbol_id}&chartType={chart_type}&side=-1&limit={bars}', false);
  xhr.send();
  return xhr.responseText;
}})();
"""
    raw = run_eval(surface, script)
    try:
        data = json.loads(raw)
        return data.get("data", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def resolve_symbol_id(surface: str, pair: str) -> int:
    """Piniaストアからsymbolを動的解決（ハードコードにない場合）"""
    script = """
(function() {
  var pinia = window.app && window.app.__vue_app__ &&
              window.app.__vue_app__.config.globalProperties.$pinia;
  if (!pinia) return '[]';
  var syms = pinia.state.value.symbol.symbols;
  return JSON.stringify(syms.map(function(s) { return {id: s.symbolId, name: s.symbolName}; }));
})();
"""
    raw = run_eval(surface, script)
    try:
        symbols = json.loads(raw)
        for s in symbols:
            name = s["name"].replace(" LIGHT", "").replace(" ", "")
            if name == pair:
                return s["id"]
    except (json.JSONDecodeError, KeyError):
        pass
    return -1


def get_chart(pair: str, surface: str, interval: str = "5m", bars: int = 100, swing_window: int = 10) -> pd.DataFrame:
    chart_type = INTERVAL_TYPE.get(interval)
    if chart_type is None:
        print(f"未対応の足種: {interval}（対応: {', '.join(INTERVAL_TYPE.keys())}）")
        sys.exit(1)

    symbol_id = SYMBOL_IDS.get(pair)
    if symbol_id is None:
        symbol_id = resolve_symbol_id(surface, pair)
    if symbol_id < 0:
        print(f"通貨ペアが見つかりません: {pair}")
        sys.exit(1)

    raw_data = fetch_ohlc(surface, symbol_id, chart_type, bars)
    if not raw_data:
        print("チャートデータの取得に失敗しました。WebTraderが開いているか確認してください。")
        sys.exit(1)

    JST = timezone(timedelta(hours=9))
    rows = []
    for item in raw_data:
        ts_ms = int(item[0])
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=JST)
        rows.append({
            "time":  dt,
            "open":  float(item[1]),
            "high":  float(item[2]),
            "low":   float(item[3]),
            "close": float(item[4]),
        })

    # APIは新しい順で返す場合があるので時系列順にソート
    rows.sort(key=lambda r: r["time"])
    df = pd.DataFrame(rows).set_index("time")

    # テクニカル指標
    df["sma20"]  = ta.sma(df["close"], length=20)
    df["sma50"]  = ta.sma(df["close"], length=50)
    df["ema9"]   = ta.ema(df["close"], length=9)
    df["rsi14"]  = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["macd"]        = macd.iloc[:, 0]
        df["macd_signal"] = macd.iloc[:, 2]
        df["macd_hist"]   = macd.iloc[:, 1]

    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None:
        df["bb_lower"] = bb.iloc[:, 0]
        df["bb_mid"]   = bb.iloc[:, 1]
        df["bb_upper"] = bb.iloc[:, 2]

    df["ema200"] = ta.ema(df["close"], length=200)

    df["atr14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # スイングロー/ハイ（SL基準用）
    df["swing_low"]  = df["low"].rolling(swing_window, min_periods=max(3, swing_window // 2)).min().shift(1)
    df["swing_high"] = df["high"].rolling(swing_window, min_periods=max(3, swing_window // 2)).max().shift(1)

    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx is not None:
        df["adx14"] = adx.iloc[:, 0]
        df["dmp14"] = adx.iloc[:, 1]
        df["dmn14"] = adx.iloc[:, 2]

    return df


def generate_signal(df: pd.DataFrame) -> dict:
    """直近バーからトレードシグナルを生成"""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    signals = []

    rsi = last.get("rsi14")
    if pd.notna(rsi):
        if rsi < 30:
            signals.append({"type": "RSI", "direction": "BUY",  "reason": f"RSI={rsi:.1f} 売られすぎ"})
        elif rsi > 70:
            signals.append({"type": "RSI", "direction": "SELL", "reason": f"RSI={rsi:.1f} 買われすぎ"})

    macd_now  = last.get("macd")
    sig_now   = last.get("macd_signal")
    macd_prev = prev.get("macd")
    sig_prev  = prev.get("macd_signal")
    if all(pd.notna(x) for x in [macd_now, sig_now, macd_prev, sig_prev]):
        if macd_prev < sig_prev and macd_now > sig_now:
            signals.append({"type": "MACD", "direction": "BUY",  "reason": "MACDゴールデンクロス"})
        elif macd_prev > sig_prev and macd_now < sig_now:
            signals.append({"type": "MACD", "direction": "SELL", "reason": "MACDデッドクロス"})

    close    = last.get("close")
    bb_upper = last.get("bb_upper")
    bb_lower = last.get("bb_lower")
    if all(pd.notna(x) for x in [close, bb_upper, bb_lower]):
        if close > bb_upper:
            signals.append({"type": "BB", "direction": "SELL", "reason": f"BB上限突破 {close:.4f}>{bb_upper:.4f}"})
        elif close < bb_lower:
            signals.append({"type": "BB", "direction": "BUY",  "reason": f"BB下限突破 {close:.4f}<{bb_lower:.4f}"})

    buys  = sum(1 for s in signals if s["direction"] == "BUY")
    sells = sum(1 for s in signals if s["direction"] == "SELL")
    if buys > sells:
        overall = "BUY"
    elif sells > buys:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    return {"overall": overall, "signals": signals, "buy_count": buys, "sell_count": sells}


def format_row(row) -> dict:
    def fmt(v):
        if pd.isna(v): return None
        return round(float(v), 5)
    return {k: fmt(v) for k, v in row.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pair", nargs="?", default="MXNJPY")
    parser.add_argument("--interval", "-i", default="5m")
    parser.add_argument("--bars", "-b", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--surface", default=SURFACE)
    parser.add_argument("--swing-window", type=int, default=10, help="スイングSL参照期間")
    args = parser.parse_args()

    pair = args.pair.upper()
    df = get_chart(pair, args.surface, args.interval, args.bars, args.swing_window)
    signal = generate_signal(df)
    last = df.iloc[-1]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if args.json:
        records = [{"time": str(idx), **format_row(row)} for idx, row in df.iterrows()]
        print(json.dumps({
            "pair": pair, "interval": args.interval, "bars": len(df),
            "source": "minfx-webtrader",
            "signal": signal, "data": records
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== {pair} {args.interval}足 ({len(df)}本) {now} [source: minfx-webtrader] ===")
        print(f"  Close:  {last['close']:.5f}")
        print(f"  SMA20:  {last.get('sma20', float('nan')):.5f}  SMA50: {last.get('sma50', float('nan')):.5f}")
        print(f"  RSI14:  {last.get('rsi14', float('nan')):.2f}")
        print(f"  MACD:   {last.get('macd', float('nan')):.5f}  Signal: {last.get('macd_signal', float('nan')):.5f}")
        print(f"  BB:     {last.get('bb_lower', float('nan')):.5f} ~ {last.get('bb_upper', float('nan')):.5f}")
        print(f"  ATR14:  {last.get('atr14', float('nan')):.5f}")
        print(f"\n--- シグナル: {signal['overall']} (BUY:{signal['buy_count']} SELL:{signal['sell_count']}) ---")
        for s in signal["signals"]:
            print(f"  [{s['type']}] {s['direction']} - {s['reason']}")
        if not signal["signals"]:
            print("  シグナルなし（様子見）")


if __name__ == "__main__":
    main()
