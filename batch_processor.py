import pandas as pd
from typing import List, Dict, Optional, Any
from data_fetcher import fetch_5min_kline
from calculator import calculate_vpu
from logger import logger


class BatchProcessor:
    def __init__(self, config: Any):
        self.config = config

    def process_stocks(
        self, stock_list: List[str], start_date: str, end_date: str
    ) -> Dict[str, pd.DataFrame]:
        results = {}
        for code in stock_list:
            try:
                logger.info(f"Batch processing: {code}")
                df = fetch_5min_kline(code, start_date, end_date)
                if not df.empty:
                    result = calculate_vpu(df, self.config, code=code)
                    results[code] = result
                else:
                    logger.warning(f"No data for {code}, skipping")
                    results[code] = pd.DataFrame()
            except Exception as e:
                logger.error(f"Failed to process {code}: {e}")
                results[code] = pd.DataFrame()
        return results

    def get_comparison_df(
        self, results: Dict[str, pd.DataFrame], metric: str = "vpu"
    ) -> pd.DataFrame:
        comparison_data = []
        for code, df in results.items():
            if not df.empty:
                temp_df = df[["date", metric]].copy()
                temp_df.columns = ["date", code]
                comparison_data.append(temp_df.set_index("date"))

        if not comparison_data:
            return pd.DataFrame()

        return pd.concat(comparison_data, axis=1).sort_index()
