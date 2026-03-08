import argparse
import os
import sys
from datetime import datetime, timedelta

import pandas as pd

from config import Config, validate_stock_code
from data_fetcher import fetch_5min_kline
from calculator import calculate_vpu
from visualizer import export_png, export_csv


def parse_args():
    parser = argparse.ArgumentParser(description="VPU Stock Liquidity Indicator CLI")
    parser.add_argument("code", help="Stock code (e.g., 600519)")
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
        choices=["summary", "png", "csv", "all"],
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
        display_df[col] = display_df[col].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )

    return display_df.to_string(index=False)


def main():
    args = parse_args()

    if not validate_stock_code(args.code):
        print(f"Error: Invalid stock code '{args.code}'")
        print(
            "Supported formats: 600xxx, 000xxx, 001xxx, 002xxx, 300xxx, 301xxx, 688xxx"
        )
        sys.exit(1)

    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)

    start_date = args.start if args.start else thirty_days_ago.strftime("%Y-%m-%d")
    end_date = args.end if args.end else today.strftime("%Y-%m-%d")

    print(f"Fetching data for {args.code} from {start_date} to {end_date}...")
    raw_df = fetch_5min_kline(args.code, start_date, end_date)

    if raw_df.empty:
        print(f"Error: No data fetched for {args.code}")
        sys.exit(1)

    cfg = Config(PRICE_UNIT=args.price_unit, TRIM_RATIO=args.trim_ratio)
    result_df = calculate_vpu(raw_df, cfg, code=args.code)

    if result_df.empty:
        print(f"Error: No valid data after calculation for {args.code}")
        sys.exit(1)

    trading_days = len(result_df)
    print(f"\nStock Code: {args.code}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Trading Days: {trading_days}")
    print()

    if args.output in ["summary", "all"]:
        print(format_summary_table(result_df))
        print()

    if args.output in ["png", "csv", "all"]:
        os.makedirs(args.output_dir, exist_ok=True)

        end_date_clean = end_date.replace("-", "")

        if args.output in ["png", "all"]:
            png_path = os.path.join(
                args.output_dir, f"{args.code}_vpu_{end_date_clean}.png"
            )
            export_png(result_df, png_path, args.code)
            print(f"PNG exported to: {png_path}")

        if args.output in ["csv", "all"]:
            csv_path = os.path.join(
                args.output_dir, f"{args.code}_vpu_{end_date_clean}.csv"
            )
            export_csv(result_df, csv_path)
            print(f"CSV exported to: {csv_path}")


if __name__ == "__main__":
    main()
