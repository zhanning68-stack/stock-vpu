import pandas as pd
import os
from typing import Optional


class ExportManager:
    @staticmethod
    def export(df: pd.DataFrame, format: str, output_path: str):
        if df.empty:
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        format = format.lower()
        if format == "csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        elif format == "excel" or format == "xlsx":
            df.to_excel(output_path, index=False)
        elif format == "json":
            df.to_json(output_path, orient="records", indent=2)
        elif format == "parquet":
            df.to_parquet(output_path)
        elif format == "html":
            df.to_html(output_path, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
