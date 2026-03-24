#!/usr/bin/env python3
"""
MXNJPY 自動売買スクリプト
ループ監視 → シグナル検出 → 成行エントリー → 逆指値SL設定 → TP達成で決済

使用方法:
  python signal_monitor.py                       # デフォルト (30m足, 8lot, RR=1.2)
  python signal_monitor.py --dry-run             # テスト実行（注文なし）
  python signal_monitor.py --lot 2 --rr 1.5     # Lot/RR指定
  python signal_monitor.py --surface surface:57  # サーフェス指定
  python signal_monitor.py --once                # 1回だけ実行
  python signal_monitor.py --swing-sl --breakeven --ema-filter --session 8-20  # フル改善版

事前条件:
  - cmux-browser で みんなのFX WebTrader が開いていること (surface:56)
  - WebTrader の新規注文画面（成行タブ）にアクセスできること
"""
import sys
import re
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = Path(__file__).parent
SURFACE = "surface:34"
POSITION_FILE = SCRIPT_DIR / "positions.json"
JST = timezone(timedelta(hours=9))

# デフォルト設定
DEFAULT_PAIR = "MXNJPY"
DEFAULT_INTERVAL = "30m"
DEFAULT_BARS = 200
DEFAULT_LOT = 8
DEFAULT_RR = 1.2
DEFAULT_ATR_MULT = 2.0
DEFAULT_ADX_THRESHOLD = 15.0
DEFAULT_MIN_SIGNALS = 2
DEFAULT_SLEEP = 300  # 秒（5分）

# MXNJPY: 1pip / 1lot ≈ 101.5円
PIP_VALUE_PER_LOT = 101.5


# ─── cmux 操作 ──────────────────────────────────────────────────────────────

def cmux_eval(surface: str, script: str, timeout: int = 15) -> str:
    result = subprocess.run(
        ["cmux", "browser", surface, "eval", script],
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()


def cmux_click(surface: str, selector: str, timeout: int = 10) -> bool:
    result = subprocess.run(
        ["cmux", "browser", surface, "click", selector],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode == 0


def cmux_fill(surface: str, selector: str, value: str, timeout: int = 10) -> bool:
    result = subprocess.run(
        ["cmux", "browser", surface, "fill", selector, value],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode == 0


def cmux_snapshot(surface: str, timeout: int = 15) -> str:
    result = subprocess.run(
        ["cmux", "browser", surface, "snapshot", "--interactive"],
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout


def get_ref(snapshot: str, link_text: str) -> str | None:
    m = re.search(rf'link "{re.escape(link_text)}"[^\n]*\[ref=(e\d+)\]', snapshot)
    return m.group(1) if m else None


def click_ref(surface: str, ref: str, timeout: int = 10) -> bool:
    result = subprocess.run(
        ["cmux", "browser", surface, "click", ref],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode == 0


# ─── ナビゲーション ─────────────────────────────────────────────────────────

def nav_new_order_market(surface: str) -> bool:
    """新規注文 → 成行 タブに移動"""
    snap = cmux_snapshot(surface)
    ref = get_ref(snap, "新規注文")
    if not ref:
        return False
    click_ref(surface, ref)
    time.sleep(0.5)
    return True


def nav_new_order_limit(surface: str) -> bool:
    """新規注文 → 指値・逆指値 タブに移動"""
    snap = cmux_snapshot(surface)
    ref = get_ref(snap, "新規注文")
    if ref:
        click_ref(surface, ref)
        time.sleep(0.5)
    snap = cmux_snapshot(surface)
    ref = get_ref(snap, "指値・逆指値")
    if not ref:
        return False
    click_ref(surface, ref)
    time.sleep(0.5)
    return True


def nav_position_view(surface: str) -> bool:
    """ポジション照会に移動"""
    snap = cmux_snapshot(surface)
    ref = get_ref(snap, "ポジション照会")
    if not ref:
        return False
    click_ref(surface, ref)
    time.sleep(0.5)
    return True


def nav_order_cancel(surface: str) -> bool:
    """注文変更・取消に移動"""
    snap = cmux_snapshot(surface)
    ref = get_ref(snap, "注文変更・取消")
    if not ref:
        return False
    click_ref(surface, ref)
    time.sleep(0.5)
    return True


# ─── レート取得 ─────────────────────────────────────────────────────────────

def get_rate(surface: str, pair: str = "MXNJPY") -> dict | None:
    """プライスボードから現在のBid/Askを取得"""
    script = r"""
var rows = document.querySelectorAll('tr');
var data = {};
for(var i=0; i<rows.length; i++){
  var cells = rows[i].querySelectorAll('td');
  if(cells.length < 4) continue;
  var name = cells[0].textContent.replace(/\s+/g,'');
  var bid = parseFloat(cells[2].textContent.trim());
  var ask = parseFloat(cells[3].textContent.trim());
  if(name && !isNaN(bid) && !isNaN(ask)){
    var key = name.replace('LIGHT','');
    if(!data[key] || String(bid).length > String(data[key].bid).length)
      data[key] = {bid:bid, ask:ask};
  }
}
JSON.stringify(data);
"""
    raw = cmux_eval(surface, script)
    try:
        rates = json.loads(raw)
        return rates.get(pair)
    except Exception:
        return None


# ─── セッション判定 ──────────────────────────────────────────────────────────

def is_active_session(dt, active_hours: tuple) -> bool:
    """JST時間でアクティブセッション判定"""
    h = dt.hour
    start, end = active_hours
    if start <= end:
        return start <= h < end
    else:  # 日をまたぐ場合（例: 21〜翌3時）
        return h >= start or h < end


# ─── チャート・シグナル ──────────────────────────────────────────────────────

def get_chart_json(surface: str, pair: str, interval: str, bars: int,
                   swing_window: int = 10) -> dict | None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "get_chart.py"),
         pair, "--interval", interval, "--bars", str(bars),
         "--surface", surface, "--swing-window", str(swing_window), "--json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def generate_signal(data: dict, min_signals: int, adx_threshold: float) -> dict | None:
    """
    RSI14 + MACD クロス + BB 突破 → min_signals以上でエントリー
    ADX > adx_threshold かつ DI方向一致でフィルター
    戻り値: {"direction":"BUY"|"SELL", "signals":[...], "atr":..., "close":...}
    """
    rows = data.get("data", [])
    if len(rows) < 2:
        return None

    last = rows[-1]
    prev = rows[-2]

    close = last.get("close")
    atr   = last.get("atr14")
    adx   = last.get("adx14")
    dmp   = last.get("dmp14")
    dmn   = last.get("dmn14")

    if close is None or atr is None:
        return None

    buy_sigs, sell_sigs = [], []

    # RSI
    rsi = last.get("rsi14")
    if rsi is not None:
        if rsi < 30:
            buy_sigs.append(f"RSI={rsi:.1f} 売られすぎ")
        elif rsi > 70:
            sell_sigs.append(f"RSI={rsi:.1f} 買われすぎ")

    # MACD クロス
    for key in ("macd", "macd_signal"):
        if last.get(key) is None or prev.get(key) is None:
            break
    else:
        mn, sn = last["macd"], last["macd_signal"]
        mp, sp = prev["macd"], prev["macd_signal"]
        if mp < sp and mn > sn:
            buy_sigs.append("MACDゴールデンクロス")
        elif mp > sp and mn < sn:
            sell_sigs.append("MACDデッドクロス")

    # BB 突破
    bb_u = last.get("bb_upper")
    bb_l = last.get("bb_lower")
    if bb_u is not None and bb_l is not None:
        if close > bb_u:
            sell_sigs.append(f"BB上限突破 {close:.4f}>{bb_u:.4f}")
        elif close < bb_l:
            buy_sigs.append(f"BB下限突破 {close:.4f}<{bb_l:.4f}")

    # 方向判定
    if len(buy_sigs) >= min_signals:
        direction = "BUY"
        sigs = buy_sigs
    elif len(sell_sigs) >= min_signals:
        direction = "SELL"
        sigs = sell_sigs
    else:
        return None

    # ADX フィルター
    if adx is not None and adx < adx_threshold:
        return None
    if dmp is not None and dmn is not None:
        if direction == "BUY" and dmp < dmn:
            return None
        if direction == "SELL" and dmn < dmp:
            return None

    return {
        "direction": direction,
        "signals":   sigs,
        "close":     close,
        "atr":       atr,
        "adx":       adx,
        "bar_time":  last.get("time"),
        "ema200":    last.get("ema200"),
        "swing_low": last.get("swing_low"),
        "swing_high": last.get("swing_high"),
    }


# ─── 注文操作 ────────────────────────────────────────────────────────────────

def place_market_order(surface: str, direction: str, lot: int) -> bool:
    """成行注文を発注"""
    if not nav_new_order_market(surface):
        print("  [ERROR] 新規注文画面への遷移に失敗")
        return False

    if lot != 1:
        cmux_fill(surface, "input[type=text]", str(float(lot)))
        time.sleep(0.3)

    b_id = "btn-order-ask" if direction == "BUY" else "btn-order-bid"
    ok = cmux_click(surface, f"button[b-id={b_id}]")
    time.sleep(2)  # 約定を待つ
    return ok


def place_stop_loss_order(surface: str, direction: str, lot: int, sl_price: float) -> bool:
    """逆指値SL注文を発注（エントリーと逆方向）"""
    if not nav_new_order_limit(surface):
        print("  [ERROR] 指値・逆指値画面への遷移に失敗")
        return False

    if lot != 1:
        cmux_fill(surface, "input[type=text]", str(float(lot)))
        time.sleep(0.3)

    # 売買方向（エントリーと逆）
    sl_side_val = "-1" if direction == "BUY" else "1"
    cmux_click(surface, f"input[name=Side][value='{sl_side_val}']")
    time.sleep(0.3)

    # 逆指値を選択
    cmux_click(surface, "input[name=ExecuteType][value='4']")
    time.sleep(0.3)

    # 価格入力
    price_str = f"{sl_price:.4f}"
    cmux_fill(surface, "input[name=price]", price_str)
    time.sleep(0.3)

    # 注文送信
    ok = cmux_click(surface, "button[b-id=btn-order-submit]")
    time.sleep(1.5)
    return ok


def close_position_by_index(surface: str, index: int = 0) -> bool:
    """指定インデックスのポジションをクイック決済"""
    if not nav_position_view(surface):
        print("  [ERROR] ポジション照会への遷移に失敗")
        return False

    script = f"""
var btns = document.querySelectorAll('button[b-id=quick-close]');
if(btns.length > {index}){{ btns[{index}].click(); 'ok'; }} else {{ 'no_position'; }}
"""
    result = cmux_eval(surface, script)
    time.sleep(1)
    if result == "no_position":
        print(f"  [WARN] クイック決済ボタン(index={index})が見つかりません")
        return False
    return True


def cancel_all_stop_orders(surface: str) -> bool:
    """逆指値SL注文を全キャンセル（一括取消）"""
    if not nav_order_cancel(surface):
        return False

    # 注文があるか確認
    check = cmux_eval(surface, "document.body.textContent.includes('データがありません') ? 'empty' : 'has';")
    if check == "empty":
        return True  # キャンセルするものなし

    # 一括取消ボタン
    script = """
var btns = document.querySelectorAll('button');
var cancel_btn = Array.from(btns).find(function(b){ return b.textContent.trim() === '一括取消'; });
if(cancel_btn){ cancel_btn.click(); 'ok'; } else { 'not_found'; }
"""
    result = cmux_eval(surface, script)
    time.sleep(1)

    if result == "not_found":
        print("  [WARN] 一括取消ボタンが見つかりません")
        return False

    # 確認ダイアログが出た場合はOKを押す
    confirm = cmux_eval(surface, """
var btns = document.querySelectorAll('button');
var ok_btn = Array.from(btns).find(function(b){ return b.textContent.trim() === 'OK' || b.textContent.trim() === 'はい'; });
if(ok_btn){ ok_btn.click(); 'confirmed'; } else { 'no_confirm'; }
""")
    time.sleep(1)
    return True


# ─── ポジション管理 ──────────────────────────────────────────────────────────

def load_positions() -> list:
    if POSITION_FILE.exists():
        try:
            return json.loads(POSITION_FILE.read_text())
        except Exception:
            return []
    return []


def save_positions(positions: list) -> None:
    POSITION_FILE.write_text(json.dumps(positions, ensure_ascii=False, indent=2))


# ─── SL計算 ─────────────────────────────────────────────────────────────────

def calc_sl_tp(direction: str, close: float, atr: float, atr_mult: float,
               rr: float, swing_sl: bool, sig: dict) -> tuple[float, float, float]:
    """SL/TP価格とSL幅を計算。戻り値: (sl_price, tp_price, sl_width)"""
    if swing_sl and direction == "BUY" and sig.get("swing_low") is not None:
        sl_candidate = sig["swing_low"] - atr * 0.5
        sl_price = sl_candidate if sl_candidate < close else (close - atr * atr_mult)
    elif swing_sl and direction == "SELL" and sig.get("swing_high") is not None:
        sl_candidate = sig["swing_high"] + atr * 0.5
        sl_price = sl_candidate if sl_candidate > close else (close + atr * atr_mult)
    else:
        if direction == "BUY":
            sl_price = close - atr * atr_mult
        else:
            sl_price = close + atr * atr_mult

    sl_width = abs(close - sl_price)
    if direction == "BUY":
        tp_price = close + sl_width * rr
    else:
        tp_price = close - sl_width * rr

    return sl_price, tp_price, sl_width


# ─── メインループ ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MXNJPY自動売買スクリプト")
    parser.add_argument("--surface",       default=SURFACE)
    parser.add_argument("--pair",          default=DEFAULT_PAIR)
    parser.add_argument("--interval",      default=DEFAULT_INTERVAL)
    parser.add_argument("--bars",          type=int,   default=DEFAULT_BARS)
    parser.add_argument("--lot",           type=int,   default=DEFAULT_LOT)
    parser.add_argument("--rr",            type=float, default=DEFAULT_RR)
    parser.add_argument("--atr-mult",      type=float, default=DEFAULT_ATR_MULT, help="SL = entry ± ATR × 値")
    parser.add_argument("--adx-threshold", type=float, default=DEFAULT_ADX_THRESHOLD)
    parser.add_argument("--min-signals",   type=int,   default=DEFAULT_MIN_SIGNALS)
    parser.add_argument("--sleep",         type=int,   default=DEFAULT_SLEEP, help="チェック間隔（秒）")
    parser.add_argument("--dry-run",       action="store_true", help="注文を発注しない（テスト用）")
    parser.add_argument("--once",          action="store_true", help="1回だけ実行して終了")
    # 新規追加オプション
    parser.add_argument("--swing-sl",      action="store_true", help="スイングロー/ハイ基準SL")
    parser.add_argument("--swing-window",  type=int, default=10, help="スイングSL参照期間")
    parser.add_argument("--breakeven",     action="store_true", help="1R到達で建値移動")
    parser.add_argument("--ema-filter",    action="store_true", help="EMA200フィルター")
    parser.add_argument("--spread",        type=float, default=0.0, help="スプレッド(pips)")
    parser.add_argument("--session",       default=None, help="取引時間帯(JST) 例: 8-20")
    parser.add_argument("--max-positions", type=int, default=1, help="最大同時ポジション数")
    args = parser.parse_args()

    # セッション時間パース
    active_hours = None
    if args.session:
        start_h, end_h = map(int, args.session.split("-"))
        active_hours = (start_h, end_h)

    print("=" * 60)
    print(f"  MXNJPY 自動売買スクリプト 起動")
    print(f"  Pair={args.pair} Interval={args.interval} Lot={args.lot}")
    print(f"  RR={args.rr} ATR×SL={args.atr_mult} ADX>{args.adx_threshold} signals>={args.min_signals}")
    print(f"  Dry-run={args.dry_run}  MaxPositions={args.max_positions}")
    if args.swing_sl:
        print(f"  SL=SwingLow/High(window={args.swing_window})")
    if args.breakeven:
        print(f"  Breakeven=ON (1R到達で建値移動)")
    if args.ema_filter:
        print(f"  EMA200 Filter=ON")
    if args.spread > 0:
        print(f"  Spread={args.spread}pips")
    if active_hours:
        print(f"  Session={args.session}時JST")
    print("=" * 60)
    print()

    while True:
        now = datetime.now(JST)
        print(f"[{now.strftime('%H:%M:%S')}] チャートデータ取得中...")

        try:
            # 1. チャートデータ取得
            data = get_chart_json(args.surface, args.pair, args.interval,
                                  args.bars, args.swing_window)
            if not data:
                print("  チャートデータ取得失敗。スキップ。")
            else:
                # 2. シグナル生成
                sig = generate_signal(data, args.min_signals, args.adx_threshold)

                # 3. EMA200フィルター
                if sig and args.ema_filter:
                    ema200 = sig.get("ema200")
                    if ema200 is not None:
                        if sig["direction"] == "BUY" and sig["close"] < ema200:
                            print(f"  [SKIP] EMA200フィルター: Close={sig['close']:.5f} < EMA200={ema200:.5f}")
                            sig = None
                        elif sig["direction"] == "SELL" and sig["close"] > ema200:
                            print(f"  [SKIP] EMA200フィルター: Close={sig['close']:.5f} > EMA200={ema200:.5f}")
                            sig = None

                # 4. セッション時間フィルター
                if sig and active_hours and not is_active_session(now, active_hours):
                    print(f"  [SKIP] セッション時間外 ({args.session}時JST)")
                    sig = None

                if sig:
                    direction = sig["direction"]
                    close     = sig["close"]
                    atr       = sig["atr"]

                    # SL/TP計算（スイングSL対応）
                    sl_price, tp_price, sl_width = calc_sl_tp(
                        direction, close, atr, args.atr_mult, args.rr,
                        args.swing_sl, sig
                    )

                    print(f"  *** シグナル: {direction} ***")
                    print(f"  シグナル内容: {', '.join(sig['signals'])}")
                    if sig["adx"]:
                        print(f"  ADX={sig['adx']:.1f}", end="")
                    print(f"  Entry≈{close:.5f}  SL={sl_price:.5f}  TP={tp_price:.5f}")
                    if args.swing_sl:
                        print(f"  SLモード: スイング({'low=' + f'{sig.get("swing_low", 0):.5f}' if direction == 'BUY' else 'high=' + f'{sig.get("swing_high", 0):.5f}'})")

                    # 最大ポジション数チェック
                    existing = load_positions()
                    open_count = sum(1 for p in existing if p.get("status") == "open")
                    already_entered = any(
                        p.get("bar_time") == sig["bar_time"] and p.get("status") == "open"
                        for p in existing
                    )

                    if open_count >= args.max_positions:
                        print(f"  [SKIP] 最大ポジション数({args.max_positions})に到達 → スキップ")
                    elif already_entered:
                        print(f"  [SKIP] このバー({sig['bar_time']})では既にエントリー済み → スキップ")
                    elif args.dry_run:
                        print("  [DRY-RUN] 注文をスキップ")
                    else:
                        # 5. 成行エントリー
                        print(f"  → {direction} 成行注文 発注...")
                        ok_entry = place_market_order(args.surface, direction, args.lot)

                        if ok_entry:
                            # 約定後の実際のレートを取得
                            time.sleep(0.5)
                            rate = get_rate(args.surface, args.pair)
                            actual_entry = close
                            if rate:
                                actual_entry = rate["ask"] if direction == "BUY" else rate["bid"]
                                sl_price, tp_price, sl_width = calc_sl_tp(
                                    direction, actual_entry, atr, args.atr_mult, args.rr,
                                    args.swing_sl, sig
                                )
                                print(f"  約定価格≈{actual_entry:.5f}  SL={sl_price:.5f}  TP={tp_price:.5f}")

                            # 6. SL 逆指値注文
                            print(f"  → SL逆指値注文 発注: {sl_price:.4f}...")
                            ok_sl = place_stop_loss_order(args.surface, direction, args.lot, sl_price)

                            if ok_sl:
                                print(f"  → 注文完了。TP={tp_price:.5f} を監視中...")
                            else:
                                print("  [WARN] SL注文に失敗。手動でSLを設定してください！")

                            # ポジション記録
                            positions = load_positions()
                            positions.append({
                                "direction":      direction,
                                "lot":            args.lot,
                                "entry_price":    actual_entry,
                                "sl_price":       sl_price,
                                "tp_price":       tp_price,
                                "initial_sl":     sl_price,
                                "bar_time":       sig["bar_time"],
                                "entry_time":     now.isoformat(),
                                "status":         "open",
                                "breakeven_done": False,
                            })
                            save_positions(positions)
                        else:
                            print("  [ERROR] 成行注文に失敗")
                else:
                    rows   = data.get("data", [])
                    last   = rows[-1] if rows else {}
                    close  = last.get("close", 0)
                    atr    = last.get("atr14", 0)
                    adx    = last.get("adx14")
                    adx_s  = f"ADX={adx:.1f}" if adx else ""
                    print(f"  シグナルなし  Close={close:.5f}  ATR={atr:.5f}  {adx_s}")

                # 7. 建値移動 + TP/SL 監視
                positions = load_positions()
                open_pos  = [p for p in positions if p.get("status") == "open"]

                if open_pos:
                    rate = get_rate(args.surface, args.pair)
                    if rate:
                        for pos_idx, pos in enumerate(open_pos):
                            d = pos["direction"]
                            tp = pos["tp_price"]
                            sl = pos["sl_price"]
                            entry = pos["entry_price"]
                            current = rate["bid"] if d == "BUY" else rate["ask"]

                            # 建値移動チェック
                            if args.breakeven and not pos.get("breakeven_done", False):
                                initial_sl = pos.get("initial_sl", sl)
                                one_r = abs(entry - initial_sl)
                                profit_reached = (d == "BUY" and current >= entry + one_r) or \
                                                 (d == "SELL" and current <= entry - one_r)

                                if profit_reached:
                                    print(f"  *** 1R到達！建値移動 Entry={entry:.5f} Current={current:.5f} ***")
                                    if not args.dry_run:
                                        cancel_all_stop_orders(args.surface)
                                        place_stop_loss_order(args.surface, d, pos["lot"], entry)
                                        print(f"  → SLを建値({entry:.5f})に移動完了")
                                    pos["sl_price"] = entry
                                    pos["breakeven_done"] = True
                                    sl = entry

                            # TP判定
                            tp_hit = (d == "BUY" and current >= tp) or \
                                     (d == "SELL" and current <= tp)

                            if tp_hit:
                                pips = abs(current - entry) * 1000
                                spread_cost = args.spread * PIP_VALUE_PER_LOT * pos["lot"] if args.spread > 0 else 0
                                pnl = pips * PIP_VALUE_PER_LOT * pos["lot"] - spread_cost

                                print(f"  *** TP達成！ {d}  TP={tp:.5f}  Current={current:.5f}  P&L={pnl:+,.0f}円 ***")
                                if not args.dry_run:
                                    if close_position_by_index(args.surface, pos_idx):
                                        print("  → クイック決済 完了")
                                        cancel_all_stop_orders(args.surface)
                                        print("  → SL逆指値注文 キャンセル完了")
                                pos["status"]       = "closed_tp"
                                pos["close_price"]  = current
                                pos["close_time"]   = now.isoformat()
                                pos["pnl"]          = round(pnl, 0)
                                pos["spread_cost"]  = round(spread_cost, 0)
                            else:
                                # SL判定
                                sl_hit = (d == "BUY" and current <= sl) or \
                                         (d == "SELL" and current >= sl)
                                if sl_hit:
                                    pips = abs(current - entry) * 1000
                                    spread_cost = args.spread * PIP_VALUE_PER_LOT * pos["lot"] if args.spread > 0 else 0
                                    pnl = -(pips * PIP_VALUE_PER_LOT * pos["lot"]) - spread_cost

                                    print(f"  SLヒット済み {d}  SL={sl:.5f}  Current={current:.5f}  P&L={pnl:+,.0f}円")
                                    pos["status"]       = "closed_sl"
                                    pos["close_price"]  = current
                                    pos["close_time"]   = now.isoformat()
                                    pos["pnl"]          = round(pnl, 0)
                                    pos["spread_cost"]  = round(spread_cost, 0)
                                else:
                                    print(f"  TP監視中: {d}  TP={tp:.5f}  Current={current:.5f}  SL={sl:.5f}")

                        save_positions(positions)

        except KeyboardInterrupt:
            print("\n停止しました。")
            break
        except Exception as e:
            import traceback
            print(f"  [ERROR] {e}")
            traceback.print_exc()

        if args.once:
            print("--once モードで終了")
            break

        print(f"  {args.sleep}秒待機...\n")
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
