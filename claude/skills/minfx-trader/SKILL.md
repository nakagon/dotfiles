---
name: minfx-trader
description: みんなのFX Webトレーダーをcmux-browserで操作するスキル。FX注文（成行・指値）、ポジション照会、決済、口座状況確認を自動化する。yfinanceで通貨ペアのリアルタイムレート取得も可能。Use when trading on みんなのFX, placing FX orders, checking positions, managing trades via cmux browser, or getting FX rates for currency pairs like MXNJPY, USDJPY, EURJPY.
---

# みんなのFX Webトレーダー操作スキル

cmux-browser経由でみんなのFXのWebトレーダーを操作するためのスキル。

## 前提知識

- WebトレーダーはVue.js SPA（`data-v-*` 属性あり）
- **snapshot refsはほぼ機能しない** — メニューリンクのみ取得可能
- **CSSセレクタ（特に `b-id` 属性）で `click` する**のが唯一の確実な操作方法
- JS `eval` での `.click()` や `dispatchEvent` はVueハンドラに到達しない
- `eval` は**読み取り専用**（DOM状態の取得）に使う

## サーフェス管理

```bash
# 開く（ログイン済みセッションが残っていれば自動ログイン）
cmux browser open "https://min-fx.jp" --json
# → surface:N を記録

# ページ読み込み待ち
cmux browser surface:N wait --load-state complete --timeout-ms 15000
```

Webトレーダーが直接開かない場合、404ページの「ウェブサイトに戻る」等からトレーダーに遷移する。

## ナビゲーション

メニューリンクはsnapshot refsで取得可能：

```bash
cmux browser surface:N snapshot --interactive
# → link "新規注文" [ref=eXXXX] 等が取れる
cmux browser surface:N click eXXXX
```

## 注文操作

### 通貨ペア・数量の確認

```bash
# 現在の数量を確認
cmux browser surface:N eval "document.querySelector('input[type=text]').value"
# → "1.0"

# 数量を変更（fillはCSSセレクタで）
cmux browser surface:N fill "input[type=text]" "3.0"
```

### 成行注文

```bash
# 売り（Bid）
cmux browser surface:N click "button[b-id=btn-order-bid]"

# 買い（Ask）
cmux browser surface:N click "button[b-id=btn-order-ask]"
```

**注意**: クリック1回で即約定する。確認ダイアログは表示されない。複数回クリックすると複数注文が入る。

### 注文結果の確認

約定履歴に遷移してテーブルを読む：

```bash
# 約定履歴メニューをクリック（snapshot refsで取得）
cmux browser surface:N click eXXXX  # 約定履歴のref

# テーブルデータを取得
cmux browser surface:N eval "var body = document.body.textContent; var idx = body.indexOf('通貨ペア区分売買'); if(idx >= 0) { body.substring(idx, idx+600).replace(/\\s+/g,' '); }"
```

## ポジション照会

```bash
# ポジション照会メニューをクリック（snapshot refsで取得）
cmux browser surface:N click eXXXX  # ポジション照会のref

# ポジション一覧を取得
cmux browser surface:N eval "var body = document.body.textContent; var idx = body.indexOf('クイック決済'); if(idx >= 0) { body.substring(idx, idx+800).replace(/\\s+/g,' '); }"
```

### 特定ポジションの確認

```bash
# 最初のクイック決済ボタンがどのポジションか確認
cmux browser surface:N eval "var btns = document.querySelectorAll('button[b-id=quick-close]'); if(btns.length > 0) { var row = btns[0].closest('tr'); JSON.stringify({count: btns.length, firstRow: row.textContent.replace(/\\s+/g,' ').substring(0,200)}); }"
```

### クイック決済

```bash
# 最初のポジションを決済（b-id=quick-close は複数存在、最初のものがクリックされる）
cmux browser surface:N click "button[b-id=quick-close]"
```

特定のポジションを決済したい場合は、`eval` でボタンの順序と対応するポジションを確認してから操作する。

## 口座状況の確認

```bash
# ページ本文から口座情報を抽出
cmux browser surface:N eval "var body = document.body.textContent; var idx = body.indexOf('実効レバレッジ'); if(idx >= 0) { body.substring(idx, idx+200).replace(/\\s+/g,' '); }"
# → "実効レバレッジ 10.7 倍 証拠金維持率 234.04% 純資産 616,759円 評価損益 129,952円 本日の損益 -円"
```

## 為替レート取得（Python）

**みんなのFX Webトレーダーのプライスボードから直接取得**。APIキー不要・制限なし・リアルタイム。

事前にWebトレーダーをcmux-browserで開いておく必要がある。

### 使い方

```bash
# MXNJPY（デフォルト）
python ~/.claude/skills/minfx-trader/scripts/get_rate.py

# 通貨ペア指定
python ~/.claude/skills/minfx-trader/scripts/get_rate.py USDJPY

# 複数ペア一括
python ~/.claude/skills/minfx-trader/scripts/get_rate.py MXNJPY USDJPY EURJPY

# サーフェス指定（デフォルト: surface:56）
python ~/.claude/skills/minfx-trader/scripts/get_rate.py --surface surface:57 MXNJPY
```

### 出力例

```
[MXNJPY]  Bid: 9.0156  Ask: 9.0174  Spread: 0.18  (2026-03-11 12:14:08)  source: minfx-webtrader
[USDJPY]  Bid: 158.2372  Ask: 158.2387  Spread: 0.15  (2026-03-11 12:14:08)  source: minfx-webtrader
```

### 仕組み

Webトレーダーのプライスボード `<table>` → `<tr>` をパースしてBid/Askを取得。
LIGHTプランと通常プランで2行あるが、精度の高い方（小数点桁数が多い方）を自動選択。

## ポジション比率取得（MyFXBook Community Outlook）

**MyFXBook API**（session認証）でトレーダーのポジション偏りを取得。

事前に `~/.claude/skills/minfx-trader/.env` に認証情報が必要：
```
MYFXBOOK_EMAIL=your@email.com
MYFXBOOK_PASSWORD=yourpassword
```

### 使い方

```bash
# MXNJPY（USDMXN + USDJPY で代替表示）
python ~/.claude/skills/minfx-trader/scripts/get_position_ratio.py MXNJPY

# 通貨ペア直接指定
python ~/.claude/skills/minfx-trader/scripts/get_position_ratio.py USDJPY

# JSON出力
python ~/.claude/skills/minfx-trader/scripts/get_position_ratio.py --json
```

### 出力例

```
※ MXNJPYはMyFXBookに存在しないため USDMXN・USDJPY で代替表示します

=== MyFXBook Community Outlook (2026-03-11 12:34:02) ===
[USDJPY]  買:  26.0% █████                 売:  74.0% ██████████████        → BUY（売り過多 — 逆張り買い検討）
[USDMXN]  買:  50.0% ██████████            売:  50.0% ██████████            → NEUTRAL
```

### MXNJPY への読み方

MXNJPYはUSDクロスで構成されるため、USDMXN・USDJPYの両方で判断する：

| ペア | 状態 | MXNJPYへの影響 |
|------|------|----------------|
| USDJPY 売り多い（JPY強い） | 円高圧力 | MXNJPY 下落要因 |
| USDJPY 買い多い（JPY弱い） | 円安圧力 | MXNJPY 上昇要因 |
| USDMXN 売り多い（MXN強い） | MXN高圧力 | MXNJPY 上昇要因 |
| USDMXN 買い多い（MXN弱い） | MXN安圧力 | MXNJPY 下落要因 |

**注意**: MXN関連ユーザー数が少ない（USDMXN: ~70ポジション）のでチャートシグナルと併用すること。

### チャートデータ取得（みんなのFX WebTrader直接取得）

**みんなのFX WebTraderのAPIから直接取得**（リアルタイム・遅延なし）。
Piniaストア + `/express/rest/pricing/chart/charts` エンドポイントを使用。

```bash
# MXNJPY デフォルト（5m足 100本）
python ~/.claude/skills/minfx-trader/scripts/get_chart.py

# 足種・本数指定
python ~/.claude/skills/minfx-trader/scripts/get_chart.py MXNJPY --interval 1m --bars 200

# JSON出力（パイプ連携用）
python ~/.claude/skills/minfx-trader/scripts/get_chart.py MXNJPY --json
```

対応足種: `1m` / `5m` / `10m` / `15m` / `30m` / `1h` / `2h`
指標: SMA20/50, EMA9, RSI14, MACD, Bollinger Bands, ATR14
シグナル: RSI過熱、MACDクロス、BB突破 → BUY/SELL/NEUTRAL 総合判断

## 逆指値注文（SL設定）

指値・逆指値タブで逆指値SL注文を設定。

```bash
# 指値・逆指値タブに移動（snapshot refsで取得）
cmux browser surface:N click eXXXX  # 指値・逆指値のref

# フォーム操作（CSSセレクタ）
# lot設定
cmux browser surface:N fill "input[type=text]" "1.0"

# 方向設定
cmux browser surface:N click "input[name=Side][value='-1']"  # 売（BUYポジのSL）
cmux browser surface:N click "input[name=Side][value='1']"   # 買（SELLポジのSL）

# 逆指値を選択（指値=3, 逆指値=4）
cmux browser surface:N click "input[name=ExecuteType][value='4']"

# 価格入力
cmux browser surface:N fill "input[name=price]" "8.7500"

# 注文送信
cmux browser surface:N click "button[b-id=btn-order-submit]"
```

## 自動売買スクリプト（signal_monitor.py）

ループ監視 → シグナル検出 → 成行エントリー → 逆指値SL設定 → TP達成で決済。

```bash
# 基本実行（30m足, 8lot, RR=1.2）
python ~/.claude/skills/minfx-trader/scripts/signal_monitor.py

# テスト（注文なし）
python ~/.claude/skills/minfx-trader/scripts/signal_monitor.py --dry-run

# 設定指定
python ~/.claude/skills/minfx-trader/scripts/signal_monitor.py --lot 2 --rr 1.5 --adx-threshold 15

# フル改善版（スイングSL + 建値移動 + EMA200フィルター + セッション制限）
python ~/.claude/skills/minfx-trader/scripts/signal_monitor.py --swing-sl --breakeven --ema-filter --session 8-20 --spread 0.18

# 1回だけ実行
python ~/.claude/skills/minfx-trader/scripts/signal_monitor.py --once --dry-run
```

### 基本オプション
| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--lot N` | 8 | ロット数 |
| `--rr N` | 1.2 | リスクリワード比 |
| `--atr-mult N` | 2.0 | SL = entry ± ATR × N |
| `--adx-threshold N` | 15.0 | ADX閾値 |
| `--min-signals N` | 2 | エントリー最低シグナル数 |
| `--interval` | 30m | チャート足種 |

### 改善オプション
| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--swing-sl` | OFF | スイングロー/ハイ基準SL（ATR固定の代わりに直近N本の高安値を使用） |
| `--swing-window N` | 10 | スイングSL参照期間（本数） |
| `--breakeven` | OFF | 1R到達で建値移動（SLをエントリー価格に移動） |
| `--ema-filter` | OFF | EMA200フィルター（トレンド方向のみエントリー） |
| `--spread N` | 0.0 | スプレッド(pips) P&L計算に反映 |
| `--session 8-20` | なし | 取引時間帯(JST) 時間外はエントリーしない |
| `--max-positions N` | 1 | 最大同時ポジション数 |

戦略: RSI14 + MACDクロス + BB突破 → 2シグナル以上 + ADX>15 でエントリー
SL: 成行後に 逆指値注文 (entry ± ATR×2 or スイングロー基準)
TP: スクリプト監視 → クイック決済 + SL逆指値キャンセル
positions.json でポジション状態を管理（P&L・スプレッドコスト記録付き）

## 重要な b-id 一覧

| b-id | 要素 | 用途 |
|------|------|------|
| `btn-order-bid` | 売りボタン | 成行売り注文 |
| `btn-order-ask` | 買いボタン | 成行買い注文 |
| `quick-close` | クイック決済ボタン | ポジション即時決済 |
| `close-order` | 決済注文ボタン | 決済注文画面での実行 |

## AI Assistant Instructions

1. **注文前に必ずユーザーに確認する** — 実際の金銭取引のため
2. **クリックは1回だけ** — 複数回クリックすると複数注文が入る
3. **snapshotはメニュー遷移にのみ使う** — フォーム要素はrefsに出ない
4. **フォーム操作はCSSセレクタ（b-id属性）で行う**
5. **状態確認は `eval` で行う** — テーブルデータやinput値の読み取り
6. 操作後は `sleep 1-2` してから結果を確認する
7. **決済時は対象ポジションを `eval` で確認してからクリックする**
