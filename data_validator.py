import contextlib
import re
from datetime import datetime

import pandas as pd


class DataValidator:
    STOCK_CODE_PATTERN = re.compile(
        r"^(sh|sz)?"
        r"(6\d{5}"  # 主板 600/601/603
        r"|000\d{3}"  # 主板 000
        r"|001\d{3}"  # 主板 001
        r"|002\d{3}"  # 中小板 002
        r"|003\d{3}"  # 主板 003
        r"|300\d{3}"  # 创业板 300
        r"|301\d{3}"  # 创业板 301
        r"|688\d{3}"  # 科创板 688
        r")$"
    )

    REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume", "amount"]

    @staticmethod
    def validate_stock_code(code: str) -> bool:
        if not code:
            return False
        return bool(DataValidator.STOCK_CODE_PATTERN.match(code.strip().lower()))

    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> bool:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return start <= end
        except ValueError:
            return False

    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_cols: list[str] | None = None) -> dict:
        if df is None or df.empty:
            return {
                "is_valid": False,
                "reason": "DataFrame is empty or None",
                "row_count": 0,
            }

        cols = required_cols or DataValidator.REQUIRED_COLUMNS
        missing_cols = [col for col in cols if col not in df.columns]

        has_required_columns = len(missing_cols) == 0
        has_nulls = False
        if has_required_columns:
            has_nulls = int(df[cols].isnull().sum().sum()) > 0
        else:
            has_nulls = True

        date_range = (None, None)
        if "date" in df.columns:
            with contextlib.suppress(TypeError, ValueError):
                date_range = (df["date"].min(), df["date"].max())

        return {
            "is_valid": has_required_columns and not has_nulls,
            "has_required_columns": has_required_columns,
            "missing_columns": missing_cols,
            "has_nulls": has_nulls,
            "date_range": date_range,
            "row_count": len(df),
        }

    @staticmethod
    def get_market_type(code: str) -> str:
        code = code.strip().lower()
        if code.startswith("sh") or code.startswith("6"):
            if code.startswith("sh688") or code.startswith("688"):
                return "STAR"
            return "MAIN_SH"
        elif code.startswith("sz") or code.startswith("0") or code.startswith("3"):
            if code.startswith("sz30") or code.startswith("30"):
                return "CHINEXT"
            return "MAIN_SZ"
        return "UNKNOWN"
