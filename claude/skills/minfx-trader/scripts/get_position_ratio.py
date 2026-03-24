#!/usr/bin/env python3
"""
MyFXBook Community Outlook API でポジション比率を取得するスクリプト。
~/.claude/skills/minfx-trader/.env に MYFXBOOK_EMAIL / MYFXBOOK_PASSWORD が必要。

使用方法:
  python get_position_ratio.py                   # 全通貨ペア
  python get_position_ratio.py MXNJPY            # 通貨ペア指定
  python get_position_ratio.py --json            # JSON出力
"""
import sys
import json
import argparse
import os
from pathlib import Path
from datetime import datetime

try:
    import urllib.request
    import urllib.parse
    import urllib.error
except ImportError:
    pass  # 標準ライブラリ


# .env を読み込む（python-dotenv がなくても動く簡易実装）
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()

MYFXBOOK_EMAIL    = os.environ.get("MYFXBOOK_EMAIL", "")
MYFXBOOK_PASSWORD = os.environ.get("MYFXBOOK_PASSWORD", "")
BASE_URL = "https://www.myfxbook.com/api"


def api_get(path: str, params: dict) -> dict:
    # session は既にURLエンコード済みなので quote_via=str で二重エンコードを防ぐ
    qs = urllib.parse.urlencode(params, quote_via=lambda s, safe, enc, err: s)
    url = f"{BASE_URL}/{path}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def login() -> str:
    """メール+パスワードでログインしセッションIDを返す"""
    if not MYFXBOOK_EMAIL or not MYFXBOOK_PASSWORD:
        print("エラー: .env に MYFXBOOK_EMAIL / MYFXBOOK_PASSWORD を設定してください")
        sys.exit(1)

    data = api_get("login.json", {"email": MYFXBOOK_EMAIL, "password": MYFXBOOK_PASSWORD})
    if data.get("error"):
        print(f"ログイン失敗: {data.get('message', data)}")
        sys.exit(1)

    return data["session"]


def get_community_outlook(session: str) -> list[dict]:
    """Community Outlook（ポジション比率）を取得"""
    data = api_get("get-community-outlook.json", {"session": session})
    if data.get("error"):
        print(f"取得失敗: {data.get('message', data)}")
        sys.exit(1)

    return data.get("symbols", [])


def get_sentiment(long: float, short: float) -> str:
    """ポジション比率からセンチメント判定（逆張り視点）"""
    if long >= 70:
        return "SELL（買い過多 — 逆張り売り検討）"
    elif short >= 70:
        return "BUY（売り過多 — 逆張り買い検討）"
    elif long >= 60:
        return "やや売り（買い優勢）"
    elif short >= 60:
        return "やや買い（売り優勢）"
    else:
        return "NEUTRAL"


def normalize_pair(name: str) -> str:
    """EURUSD → EURUSD、EUR/USD → EURUSD に正規化"""
    return name.replace("/", "").upper()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pair", nargs="?", default=None, help="通貨ペア（例: MXNJPY）")
    parser.add_argument("--json", action="store_true", help="JSON出力")
    args = parser.parse_args()

    session = login()
    symbols = get_community_outlook(session)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ratios = []

    for s in symbols:
        pair = normalize_pair(s.get("name", ""))
        long_pct  = float(s.get("longPercentage",  0))
        short_pct = float(s.get("shortPercentage", 0))
        ratios.append({
            "pair":       pair,
            "buy_ratio":  long_pct,
            "sell_ratio": short_pct,
            "sentiment":  get_sentiment(long_pct, short_pct),
            "time":       now,
        })

    # フィルタ
    if args.pair:
        target = normalize_pair(args.pair)
        # MXNJPY はMyFXBookに存在しないため USDMXN+USDJPY で代替
        if target == "MXNJPY":
            ratios = [r for r in ratios if r["pair"] in ("USDMXN", "USDJPY")]
            print("※ MXNJPYはMyFXBookに存在しないため USDMXN・USDJPY で代替表示します")
        else:
            ratios = [r for r in ratios if r["pair"] == target]

    if not ratios:
        available = [r["pair"] for r in ratios[:10]]
        print(f"データが見つかりませんでした。利用可能なペア例: {available}")
        sys.exit(1)

    if args.json:
        print(json.dumps(ratios, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== MyFXBook Community Outlook ({now}) ===")
        for r in ratios:
            bar_buy  = "█" * int(r["buy_ratio"]  / 5)
            bar_sell = "█" * int(r["sell_ratio"] / 5)
            print(f"[{r['pair']}]  買: {r['buy_ratio']:5.1f}% {bar_buy:<20}  売: {r['sell_ratio']:5.1f}% {bar_sell:<20}  → {r['sentiment']}")


if __name__ == "__main__":
    main()
