import time

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

REQUEST_INTERVAL = 2
MAX_RETRIES = 3
RETRY_BACKOFF = 5


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

        start_datetime_str = start_dt.strftime("%Y-%m-%d 09:30:00")
        end_datetime_str = end_dt.strftime("%Y-%m-%d 15:00:00")

        print(f"  Fetching unadjusted 5min data...")
        unadjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_hist_min_em(
                symbol=code,
                period="5",
                adjust="",
                start_date=start_datetime_str,
                end_date=end_datetime_str,
            ),
            "unadjusted 5min",
        )

        print(f"  Fetching adjusted 5min data...")
        adjusted_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_hist_min_em(
                symbol=code,
                period="5",
                adjust="qfq",
                start_date=start_datetime_str,
                end_date=end_datetime_str,
            ),
            "adjusted 5min",
        )

        if unadjusted_df is None or adjusted_df is None:
            return pd.DataFrame()
        if unadjusted_df.empty or adjusted_df.empty:
            return pd.DataFrame()

        unadjusted_rename = {
            "时间": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }
        unadjusted_df = unadjusted_df[list(unadjusted_rename.keys())].rename(
            columns=unadjusted_rename
        )

        adjusted_rename = {
            "时间": "date",
            "开盘": "adj_open",
            "收盘": "adj_close",
            "最高": "adj_high",
            "最低": "adj_low",
        }
        adjusted_df = adjusted_df[list(adjusted_rename.keys())].rename(
            columns=adjusted_rename
        )

        result_df = unadjusted_df.copy()
        result_df["adj_open"] = adjusted_df["adj_open"]
        result_df["adj_high"] = adjusted_df["adj_high"]
        result_df["adj_low"] = adjusted_df["adj_low"]
        result_df["adj_close"] = adjusted_df["adj_close"]

        result_df["date"] = pd.to_datetime(result_df["date"])
        result_df = result_df[
            (result_df["date"] >= pd.to_datetime(start_date))
            & (result_df["date"] <= pd.to_datetime(end_date) + timedelta(days=1))
        ]

        daily_start_date = (start_dt - timedelta(days=10)).strftime("%Y%m%d")
        daily_end_date = end_dt.strftime("%Y%m%d")

        print(f"  Fetching daily data for prev_close...")
        daily_df = _fetch_with_retry(
            lambda: ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                adjust="",
                start_date=daily_start_date,
                end_date=daily_end_date,
            ),
            "daily kline",
        )

        if daily_df is not None and not daily_df.empty:
            daily_rename = {
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            }
            daily_df = daily_df[list(daily_rename.keys())].rename(columns=daily_rename)
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            daily_df = daily_df.sort_values("date")
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
