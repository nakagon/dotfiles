#!/usr/bin/env python3
"""
FX為替レート取得スクリプト（みんなのFX Webトレーダーから直接取得）
事前にcmux-browserでWebトレーダーを開いておく必要がある。

使用方法:
  python get_rate.py                        # MXNJPY（デフォルト）
  python get_rate.py USDJPY                 # 通貨ペア指定
  python get_rate.py MXNJPY USDJPY EURJPY  # 複数指定
  python get_rate.py --surface surface:56 MXNJPY  # サーフェス指定
"""
import sys
import json
import subprocess
from datetime import datetime


SURFACE = "surface:34"  # デフォルトサーフェス


def parse_args(argv: list[str]) -> tuple[str, list[str]]:
    surface = SURFACE
    pairs = []
    i = 1
    while i < len(argv):
        if argv[i] == "--surface" and i + 1 < len(argv):
            surface = argv[i + 1]
            i += 2
        else:
            pairs.append(argv[i].upper())
            i += 1
    return surface, pairs or ["MXNJPY"]


def run_eval(surface: str, script: str) -> str:
    result = subprocess.run(
        ["cmux", "browser", surface, "eval", script],
        capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip()


def get_rates(surface: str, pairs: list[str]) -> list[dict]:
    """Webトレーダーのプライスボードテーブルから全レートを取得"""
    script = """
var rows = document.querySelectorAll('tr');
var data = {};
for(var i=0; i<rows.length; i++) {
  var cells = rows[i].querySelectorAll('td');
  if(cells.length < 4) continue;
  var name = cells[0].textContent.replace(/\\s+/g,'');
  var bid = parseFloat(cells[2].textContent.trim());
  var ask = parseFloat(cells[3].textContent.trim());
  var sp  = parseFloat(cells[4].textContent.trim());
  if(name && !isNaN(bid) && !isNaN(ask)) {
    // LIGHTサフィックスを除去して正規化
    var key = name.replace('LIGHT','');
    // 精度の高い方（小数点多い方）を優先
    if(!data[key] || String(bid).length > String(data[key].bid).length) {
      data[key] = {bid: bid, ask: ask, spread: sp};
    }
  }
}
JSON.stringify(data);
"""
    raw = run_eval(surface, script)
    try:
        all_rates = json.loads(raw)
    except json.JSONDecodeError:
        return []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for pair in pairs:
        rate = all_rates.get(pair)
        if rate:
            results.append({
                "pair": pair,
                "bid": rate["bid"],
                "ask": rate["ask"],
                "spread": rate["spread"],
                "source": "minfx-webtrader",
                "time": now,
            })
        else:
            results.append({
                "pair": pair,
                "error": f"not found in priceboard (available: {', '.join(list(all_rates.keys())[:5])}...)",
                "time": now,
            })
    return results


def main():
    surface, pairs = parse_args(sys.argv)

    results = get_rates(surface, pairs)

    for r in results:
        if "error" in r:
            print(f"[{r['pair']}]  ERROR: {r['error']}")
        else:
            print(f"[{r['pair']}]  Bid: {r['bid']}  Ask: {r['ask']}  Spread: {r['spread']}  ({r['time']})  source: {r['source']}")

    if len(pairs) > 1:
        print("\n--- JSON ---")
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
