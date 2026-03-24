#!/usr/bin/env python3
"""見積書PDF生成スクリプト

Usage:
    python3 generate_pdf.py <estimate.yaml> [--config config.yaml] [--output output.pdf]
"""

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"
DEFAULT_CONFIG = SKILL_DIR / "config.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def compute_amounts(data: dict) -> dict:
    """明細の金額計算と合計算出"""
    tax_rate = data.get("tax_rate", 0.10)

    has_notes = False
    for item in data["items"]:
        item["amount"] = item["quantity"] * item["unit_price"]
        if item.get("note"):
            has_notes = True

    subtotal = sum(item["amount"] for item in data["items"])
    tax_amount = math.floor(subtotal * tax_rate)
    total_with_tax = subtotal + tax_amount

    data["subtotal"] = subtotal
    data["tax_rate"] = tax_rate
    data["tax_amount"] = tax_amount
    data["total_with_tax"] = total_with_tax
    data["has_notes"] = has_notes

    # テーブルの空行数（最低10行になるように）
    min_rows = 10
    data["empty_rows"] = max(0, min_rows - len(data["items"]))

    return data


def apply_defaults(data: dict, config: dict) -> dict:
    """設定ファイルのデフォルト値を適用"""
    defaults = config.get("defaults", {})

    # 税率
    if "tax_rate" not in data:
        data["tax_rate"] = defaults.get("tax_rate", 0.10)

    # 日付
    if not data.get("date"):
        data["date"] = datetime.now().strftime("%Y年%m月%d日")
    elif "-" in str(data["date"]):
        # YYYY-MM-DD → YYYY年MM月DD日
        try:
            dt = datetime.strptime(str(data["date"]), "%Y-%m-%d")
            data["date"] = dt.strftime("%Y年%m月%d日")
        except ValueError:
            pass

    # 備考デフォルト
    if not data.get("notes"):
        data["notes"] = defaults.get("notes", "")

    # 会社情報
    data["company"] = config.get("company", {})

    return data


def generate_pdf(data: dict, output_path: Path) -> None:
    """HTMLテンプレートからPDF生成"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("estimate.html")

    html_content = template.render(**data)

    html = HTML(
        string=html_content,
        base_url=str(TEMPLATE_DIR),
    )
    html.write_pdf(str(output_path))


def main():
    parser = argparse.ArgumentParser(description="見積書PDF生成")
    parser.add_argument("estimate_yaml", help="見積データYAMLファイル")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help=f"会社情報設定ファイル (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="出力PDFパス (default: ~/Desktop/見積書_{番号}.pdf)",
    )
    args = parser.parse_args()

    # データ読み込み
    estimate_path = Path(args.estimate_yaml)
    if not estimate_path.exists():
        print(f"Error: {estimate_path} が見つかりません", file=sys.stderr)
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: 設定ファイル {config_path} が見つかりません", file=sys.stderr)
        print("  cp config.yaml.sample config.yaml して設定してください", file=sys.stderr)
        sys.exit(1)

    data = load_yaml(estimate_path)
    config = load_yaml(config_path)

    # デフォルト適用 → 金額計算
    data = apply_defaults(data, config)
    data = compute_amounts(data)

    # 出力パス
    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        output_dir = Path(config.get("defaults", {}).get("output_dir", "~/Desktop")).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = output_dir / f"見積書_{safe_ts}.pdf"

    # PDF生成
    generate_pdf(data, output_path)
    print(f"PDF生成完了: {output_path}")
    print(f"  合計（税込）: ¥{data['total_with_tax']:,.0f}")


if __name__ == "__main__":
    main()
