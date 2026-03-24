---
name: estimate-generator
description: 見積書を統一フォーマットでPDF作成する。概算見積・正式見積の両方に対応。Use when creating estimates, quotations, 見積書, 概算, PDF見積, or generating business documents for clients.
---

# 見積書ジェネレーター

統一フォーマットで概算・正式見積書をPDF出力するスキル。

## When to Use This Skill

- 見積書・見積PDF を作成したいとき
- 概算見積を素早く出したいとき
- 正式見積を統一フォーマットで作成したいとき
- クライアント向け見積書が必要なとき

## 初回セットアップ

1. 会社情報を設定ファイルに登録:

```bash
cp ~/.claude/skills/estimate-generator/config.yaml.sample ~/.claude/skills/estimate-generator/config.yaml
# config.yaml を編集して自社情報を入力
```

2. 依存パッケージ（初回のみ）:

```bash
pip3 install weasyprint jinja2 pyyaml
```

## 見積タイプ

| タイプ | `type` | 特徴 |
|--------|--------|------|
| 概算見積 | `rough` | 「概算」透かし表示、有効期限短め（デフォルト1週間） |
| 正式見積 | `formal` | 正式書類、有効期限長め（デフォルト1ヶ月） |

## ワークフロー

### Step 1: ユーザーから見積内容をヒアリング

必要情報:
- 宛先（会社名、部署、担当者）
- 件名
- 明細（項目名、数量、単位、単価）
- 概算 or 正式
- 備考・支払条件（あれば）

### Step 2: 見積データYAMLを生成

`/tmp/estimate_XXXX.yaml` に書き出す。フォーマットは下記「データフォーマット」参照。

### Step 3: PDF生成スクリプト実行

```bash
python3 ~/.claude/skills/estimate-generator/scripts/generate_pdf.py \
  /tmp/estimate_XXXX.yaml \
  --config ~/.claude/skills/estimate-generator/config.yaml \
  --output ~/Desktop/見積書_XXXX.pdf
```

### Step 4: 出力パスをユーザーに伝える

## データフォーマット (YAML)

```yaml
type: formal          # formal | rough
number: "EST-2026-0001"
date: "2026-03-07"
valid_until: "2026-04-06"  # 省略時: rough=1週間後, formal=1ヶ月後

client:
  name: "株式会社サンプル"
  department: "システム開発部"  # 省略可
  person: "山田太郎"            # 省略可

subject: "Webアプリケーション開発"

items:
  - name: "要件定義"
    quantity: 1
    unit: "式"
    unit_price: 500000
    note: ""                    # 省略可
  - name: "設計・開発"
    quantity: 3
    unit: "人月"
    unit_price: 800000
  - name: "テスト・品質管理"
    quantity: 1
    unit: "式"
    unit_price: 300000

tax_rate: 0.10                  # デフォルト10%

notes: |
  お支払い条件: 納品月末締め翌月末払い

remarks: ""                     # 特記事項（省略可）
```

## 見積番号の採番規則

- フォーマット: `EST-YYYY-NNNN`
- YYYY: 年度
- NNNN: 連番（0001から）
- ユーザーが指定しない場合は日時ベースで自動生成: `EST-2026-0307-1830`

## AI Assistant Instructions

このスキルが起動したら:

1. **設定ファイル確認**: `~/.claude/skills/estimate-generator/config.yaml` を Read で確認。なければセットアップを案内
2. **ヒアリング**: 宛先・件名・明細・見積タイプを確認。ユーザーが曖昧な場合は AskUserQuestion で選択肢を提示
3. **YAML生成**: `/tmp/estimate_{番号}.yaml` にデータを Write
4. **PDF生成**: `generate_pdf.py` を Bash で実行
5. **結果報告**: PDFパスと金額サマリーを伝える

注意:
- 金額計算は必ずスクリプト側で行う（Claude側で計算ミスしない）
- 税率はデフォルト10%。ユーザー指定があれば変更
- 概算の場合は valid_until を短めに設定
- 見積番号はユーザー指定を優先。なければ自動採番
- 出力先はデフォルト `~/Desktop/`。ユーザー指定があれば変更
