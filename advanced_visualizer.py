import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from visualizer import wrap_js_code


class AdvancedVisualizer:
    @staticmethod
    def render_comparison_chart(
        comparison_df: pd.DataFrame, title: str = "Stock Comparison"
    ):
        if comparison_df.empty:
            return {}

        dates = comparison_df.index.astype(str).tolist()
        series = []
        for col in comparison_df.columns:
            series.append(
                {
                    "name": col,
                    "type": "line",
                    "data": comparison_df[col].tolist(),
                    "smooth": True,
                }
            )

        option = {
            "title": {
                "text": title,
                "left": "center",
                "textStyle": {"color": "#e0e0e0"},
            },
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "rgba(20,20,30,0.9)",
                "textStyle": {"color": "#e0e0e0"},
            },
            "legend": {
                "data": comparison_df.columns.tolist(),
                "top": "10%",
                "textStyle": {"color": "#aaa"},
            },
            "xAxis": {
                "type": "category",
                "data": dates,
                "axisLabel": {"color": "#aaa"},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {"color": "#aaa"},
                "splitLine": {
                    "lineStyle": {"color": "rgba(255,255,255,0.06)", "type": "dashed"}
                },
            },
            "series": series,
            "dataZoom": [{"type": "slider", "bottom": "0%"}],
        }
        return option

    @staticmethod
    def render_correlation_matrix(comparison_df: pd.DataFrame):
        if comparison_df.empty or len(comparison_df.columns) < 2:
            return {}

        corr = comparison_df.corr().round(2)
        cols = corr.columns.tolist()
        data = []
        for i in range(len(cols)):
            for j in range(len(cols)):
                data.append([i, j, float(corr.iloc[i, j])])

        option = {
            "title": {
                "text": "Correlation Matrix",
                "left": "center",
                "textStyle": {"color": "#e0e0e0"},
            },
            "tooltip": {"position": "top"},
            "grid": {"height": "70%", "top": "15%"},
            "xAxis": {
                "type": "category",
                "data": cols,
                "splitArea": {"show": True},
                "axisLabel": {"color": "#aaa"},
            },
            "yAxis": {
                "type": "category",
                "data": cols,
                "splitArea": {"show": True},
                "axisLabel": {"color": "#aaa"},
            },
            "visualMap": {
                "min": -1,
                "max": 1,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "0%",
                "inRange": {"color": ["#00c878", "#ffffff", "#ff4b4b"]},
            },
            "series": [
                {
                    "name": "Correlation",
                    "type": "heatmap",
                    "data": data,
                    "label": {"show": True, "color": "#000"},
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.5)",
                        }
                    },
                }
            ],
        }
        return option
