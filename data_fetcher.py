import time

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

REQUEST_INTERVAL = 2
MAX_RETRIES = 3
RETRY_BACKOFF = 5


def _to_sina_symbol(code: str) -> str:
    code = code.strip().lower()
    if code.startswith("sh") or code.startswith("sz"):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def _fetch_with_retry(fetch_fn, description: str):
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                wait = RETRY_BACKOFF * attempt
                print(
                    f"  Retry {attempt}/{MAX_RETRIES} for {description}, waiting {wait}s..."
                )
                time.sleep(wait)
            result = fetch_fn()
            time.sleep(REQUEST_INTERVAL)
            return result
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            print(f"  {description} failed: {e}")
    return None


def fetch_5min_kline(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        sina_symbol = _to_sina_symbol(code)

        print("  Fetching unadjusted 5min data (Sina)...")
        unadjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_minute(
                symbol=sina_symbol,
                period="5",
                adjust="",
            ),
            "sina unadjusted 5min",
        )

        print("  Fetching adjusted 5min data (Sina)...")
        adjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_minute(
                symbol=sina_symbol,
                period="5",
                adjust="qfq",
            ),
            "sina adjusted 5min",
        )

        if unadjusted_df is None or adjusted_df is None:
            return pd.DataFrame()
        if unadjusted_df.empty or adjusted_df.empty:
            return pd.DataFrame()

        unadjusted_rename = {
            "day": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "amount": "amount",
        }
        unadjusted_df = unadjusted_df[list(unadjusted_rename.keys())].rename(
            columns=unadjusted_rename
        )

        adjusted_rename = {
            "day": "date",
            "open": "adj_open",
            "high": "adj_high",
            "low": "adj_low",
            "close": "adj_close",
        }
        adjusted_df = adjusted_df[list(adjusted_rename.keys())].rename(
            columns=adjusted_rename
        )

        unadjusted_df["date"] = pd.to_datetime(unadjusted_df["date"])
        adjusted_df["date"] = pd.to_datetime(adjusted_df["date"])

        for col in ["open", "high", "low", "close", "volume", "amount"]:
            unadjusted_df[col] = pd.to_numeric(unadjusted_df[col], errors="coerce")
        for col in ["adj_open", "adj_high", "adj_low", "adj_close"]:
            adjusted_df[col] = pd.to_numeric(adjusted_df[col], errors="coerce")

        result_df = unadjusted_df.merge(
            adjusted_df,
            on="date",
            how="left",
        )

        result_df = result_df[
            (result_df["date"] >= pd.to_datetime(start_date))
            & (result_df["date"] <= pd.to_datetime(end_date) + timedelta(days=1))
        ]

        daily_start = start_dt - timedelta(days=10)
        daily_end = end_dt

        print("  Fetching daily data for prev_close (Sina)...")
        daily_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_daily(symbol=sina_symbol, adjust=""),
            "sina daily kline",
        )

        if daily_df is not None and not daily_df.empty:
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            for col in ["open", "high", "low", "close", "volume", "amount"]:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_numeric(daily_df[col], errors="coerce")
            daily_df = daily_df.sort_values("date")
            daily_df = daily_df[
                (daily_df["date"] >= daily_start) & (daily_df["date"] <= daily_end)
            ]
            daily_df["prev_close"] = daily_df["close"].shift(1)

            prev_close_map = dict(zip(daily_df["date"].dt.date, daily_df["prev_close"]))
            result_df["prev_close"] = result_df["date"].dt.date.map(prev_close_map)
            result_df["prev_close"] = result_df["prev_close"].fillna(result_df["close"])
        else:
            result_df["prev_close"] = (
                result_df["close"].shift(1).fillna(result_df["close"])
            )

        column_order = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "prev_close",
            "adj_open",
            "adj_high",
            "adj_low",
            "adj_close",
        ]
        result_df = result_df[column_order]

        return result_df

    except Exception as e:
        print(f"Error fetching data for {code}: {str(e)}")
        return pd.DataFrame()
