import time
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from logger import logger
from cache_manager import CacheManager
from data_validator import DataValidator

cache = CacheManager(cache_dir="./cache", ttl_hours=24)

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
                logger.info(
                    f"Retry {attempt}/{MAX_RETRIES} for {description}, waiting {wait}s..."
                )
                time.sleep(wait)
            result = fetch_fn()
            time.sleep(REQUEST_INTERVAL)
            return result
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"{description} final attempt failed: {e}")
                raise
            logger.warning(f"{description} attempt {attempt + 1} failed: {e}")
    return None


def fetch_5min_kline(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    if not DataValidator.validate_stock_code(code):
        logger.error(f"Invalid stock code: {code}")
        return pd.DataFrame()

    if not DataValidator.validate_date_range(start_date, end_date):
        logger.error(f"Invalid date range: {start_date} to {end_date}")
        return pd.DataFrame()

    cache_key = cache.get_cache_key(
        code=code, start=start_date, end=end_date, type="5min_kline"
    )
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Using cached data for {code}")
        return cached_data

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        sina_symbol = _to_sina_symbol(code)

        logger.info(f"Fetching 5min data for {code} ({start_date} to {end_date})")

        unadjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_minute(symbol=sina_symbol, period="5", adjust=""),
            "sina unadjusted 5min",
        )

        adjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_minute(symbol=sina_symbol, period="5", adjust="qfq"),
            "sina adjusted 5min",
        )

        if (
            unadjusted_df is None
            or adjusted_df is None
            or unadjusted_df.empty
            or adjusted_df.empty
        ):
            logger.warning(f"No 5min data returned for {code}")
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

        result_df = unadjusted_df.merge(adjusted_df, on="date", how="left")

        result_df = result_df[
            (result_df["date"] >= pd.to_datetime(start_date))
            & (result_df["date"] <= pd.to_datetime(end_date) + timedelta(days=1))
        ]

        daily_start = start_dt - timedelta(days=10)
        daily_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_daily(symbol=sina_symbol, adjust=""),
            "sina daily kline",
        )

        if daily_df is not None and not daily_df.empty:
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            daily_df = daily_df.sort_values("date")
            daily_df = daily_df[
                (daily_df["date"] >= daily_start) & (daily_df["date"] <= end_dt)
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

        cache.set(cache_key, result_df)

        return result_df

    except Exception as e:
        logger.error(f"Error fetching data for {code}: {str(e)}")
        return pd.DataFrame()
