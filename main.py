import argparse
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

from calculator import calculate_vpu
from config import Config, validate_stock_code
from data_fetcher import fetch_5min_kline
from export_manager import ExportManager
from visualizer import export_png


def parse_args():
    parser = argparse.ArgumentParser(description="VPU Stock Liquidity Indicator CLI")
    parser.add_argument("code", help="Stock code or codes (comma separated, e.g., 600519,000858)")
    parser.add_argument(
        "-s",
        "--start",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD), default: 30 days ago",
    )
    parser.add_argument(
        "-e",
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD), default: today",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        choices=["summary", "png", "csv", "xlsx", "json", "parquet", "all"],
        default="summary",
        help="Output mode (default: summary)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--price-unit",
        type=float,
        default=0.05,
        help="Price unit (default: 0.05)",
    )
    parser.add_argument(
        "--trim-ratio",
        type=float,
        default=0.25,
        help="Trim ratio (default: 0.25)",
    )
    return parser.parse_args()


def format_summary_table(result_df: pd.DataFrame) -> str:
    display_cols = ["date", "vpu", "vpu_up", "vpu_down", "close_price"]
    display_df = result_df[display_cols].copy()
    display_df["date"] = display_df["date"].astype(str)

    for col in ["vpu", "vpu_up", "vpu_down", "close_price"]:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")

    return display_df.to_string(index=False)


def main():
    args = parse_args()

    stock_codes = [c.strip() for c in args.code.split(",") if c.strip()]
    valid_codes = []
    for code in stock_codes:
        if validate_stock_code(code):
            valid_codes.append(code)
        else:
            print(f"Warning: Invalid stock code '{code}' ignored.")

    if not valid_codes:
        print("Error: No valid stock codes provided.")
        sys.exit(1)

    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    start_date = args.start if args.start else thirty_days_ago.strftime("%Y-%m-%d")
    end_date = args.end if args.end else today.strftime("%Y-%m-%d")

    cfg = Config(PRICE_UNIT=args.price_unit, TRIM_RATIO=args.trim_ratio)

    for code in valid_codes:
        print(f"\nProcessing {code} from {start_date} to {end_date}...")
        raw_df = fetch_5min_kline(code, start_date, end_date)

        if raw_df.empty:
            print(f"Error: No data fetched for {code}")
            continue

        result_df = calculate_vpu(raw_df, cfg, code=code)

        if result_df.empty:
            print(f"Error: No valid data after calculation for {code}")
            continue

        trading_days = len(result_df)
        print(f"Stock Code: {code}")
        print(f"Trading Days: {trading_days}")

        if args.output in ["summary", "all"]:
            print(format_summary_table(result_df))

        if args.output != "summary":
            os.makedirs(args.output_dir, exist_ok=True)
            end_date_clean = end_date.replace("-", "")

            if args.output in ["png", "all"]:
                png_path = os.path.join(args.output_dir, f"{code}_vpu_{end_date_clean}.png")
                export_png(result_df, png_path, code)
                print(f"PNG exported to: {png_path}")

            formats = ["csv", "xlsx", "json", "parquet"]
            for fmt in formats:
                if args.output == fmt or args.output == "all":
                    out_path = os.path.join(args.output_dir, f"{code}_vpu_{end_date_clean}.{fmt}")
                    ExportManager.export(result_df, fmt, out_path)
                    print(f"{fmt.upper()} exported to: {out_path}")


if __name__ == "__main__":
    main()
