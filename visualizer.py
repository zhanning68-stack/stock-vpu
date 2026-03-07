import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from streamlit_echarts import JsCode


def wrap_js_code(obj):
    if isinstance(obj, dict):
        return {k: wrap_js_code(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [wrap_js_code(item) for item in obj]
    elif isinstance(obj, str) and obj.strip().startswith("function"):
        return JsCode(obj)
    return obj


def render_chart(result_df: pd.DataFrame, stock_code: str = "") -> dict:
    dates = result_df["date"].astype(str).tolist()
    vpu_up = result_df["vpu_up"].tolist()
    vpu_down = (-result_df["vpu_down"].abs()).tolist()
    ma5 = result_df["ma5"].tolist()
    close_price = result_df["close_price"].tolist()

    title_text = (
        f"VPU 流动性深度指标 — {stock_code}" if stock_code else "VPU 流动性深度指标"
    )

    tooltip_formatter = (
        "function(params) {"
        "  var date = params[0].axisValue;"
        "  var html = '<b>' + date + '</b><br/>';"
        "  params.forEach(function(p) {"
        "    var val = p.value;"
        "    if (p.seriesName === 'VPU_Down (支撑)') val = Math.abs(val);"
        "    var display = (p.seriesName === '收盘价')"
        "      ? ('¥ ' + val)"
        "      : (val !== null ? val.toLocaleString() + ' 手' : '-');"
        "    html += p.marker + ' ' + p.seriesName + ': ' + display + '<br/>';"
        "  });"
        "  return html;"
        "}"
    )

    yaxis_label_formatter = (
        "function(value) { return Math.abs(value).toLocaleString(); }"
    )

    return {
        "title": {
            "text": title_text,
            "textStyle": {"color": "#333", "fontSize": 16},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": tooltip_formatter,
        },
        "legend": {
            "data": ["VPU_Up (抛压)", "VPU_Down (支撑)", "MA5", "收盘价"],
            "top": 40,
            "textStyle": {"color": "#555"},
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "12%",
            "top": "15%",
            "containLabel": True,
        },
        "xAxis": [
            {
                "type": "category",
                "data": dates,
                "axisTick": {"alignWithLabel": True},
                "axisLabel": {"color": "#666"},
            }
        ],
        "yAxis": [
            {
                "type": "value",
                "name": "VPU (手/0.05元)",
                "position": "left",
                "axisLabel": {
                    "color": "#666",
                    "formatter": yaxis_label_formatter,
                },
                "splitLine": {"lineStyle": {"type": "dashed", "color": "#eee"}},
            },
            {
                "type": "value",
                "name": "收盘价 (元)",
                "position": "right",
                "axisLabel": {"color": "#666"},
                "splitLine": {"show": False},
                "scale": True,
            },
        ],
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "bottom": 0, "height": 20},
        ],
        "series": [
            {
                "name": "VPU_Up (抛压)",
                "type": "bar",
                "stack": "Total",
                "itemStyle": {"color": "#eb5454", "opacity": 0.8},
                "data": vpu_up,
            },
            {
                "name": "VPU_Down (支撑)",
                "type": "bar",
                "stack": "Total",
                "itemStyle": {"color": "#47b262", "opacity": 0.8},
                "data": vpu_down,
            },
            {
                "name": "MA5",
                "type": "line",
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"color": "#e6a23c", "width": 3},
                "data": ma5,
            },
            {
                "name": "收盘价",
                "type": "line",
                "yAxisIndex": 1,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": "#333333", "width": 2, "type": "dashed"},
                "itemStyle": {
                    "color": "#333333",
                    "borderWidth": 2,
                    "borderColor": "#fff",
                },
                "data": close_price,
            },
        ],
    }


def render_apu_chart(result_df: pd.DataFrame, stock_code: str = "") -> dict:
    dates = result_df["date"].astype(str).tolist()
    apu = result_df["apu"].tolist()
    close_price = result_df["close_price"].tolist()

    title_text = (
        f"APU 成交额深度指标 — {stock_code}" if stock_code else "APU 成交额深度指标"
    )

    tooltip_formatter = (
        "function(params) {"
        "  var date = params[0].axisValue;"
        "  var html = '<b>' + date + '</b><br/>';"
        "  params.forEach(function(p) {"
        "    var val = p.value;"
        "    var display = (p.seriesName === '收盘价')"
        "      ? ('¥ ' + val)"
        "      : (val !== null ? val.toLocaleString() + ' 元' : '-');"
        "    html += p.marker + ' ' + p.seriesName + ': ' + display + '<br/>';"
        "  });"
        "  return html;"
        "}"
    )

    return {
        "title": {
            "text": title_text,
            "textStyle": {"color": "#333", "fontSize": 16},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": tooltip_formatter,
        },
        "legend": {
            "data": ["APU (成交额)", "收盘价"],
            "top": 40,
            "textStyle": {"color": "#555"},
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "12%",
            "top": "15%",
            "containLabel": True,
        },
        "xAxis": [
            {
                "type": "category",
                "data": dates,
                "axisTick": {"alignWithLabel": True},
                "axisLabel": {"color": "#666"},
            }
        ],
        "yAxis": [
            {
                "type": "value",
                "name": "APU (元/0.05元)",
                "position": "left",
                "axisLabel": {"color": "#666"},
                "splitLine": {"lineStyle": {"type": "dashed", "color": "#eee"}},
            },
            {
                "type": "value",
                "name": "收盘价 (元)",
                "position": "right",
                "axisLabel": {"color": "#666"},
                "splitLine": {"show": False},
                "scale": True,
            },
        ],
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "bottom": 0, "height": 20},
        ],
        "series": [
            {
                "name": "APU (成交额)",
                "type": "bar",
                "itemStyle": {"color": "#5470c6", "opacity": 0.8},
                "data": apu,
            },
            {
                "name": "收盘价",
                "type": "line",
                "yAxisIndex": 1,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": "#333333", "width": 2, "type": "dashed"},
                "itemStyle": {
                    "color": "#333333",
                    "borderWidth": 2,
                    "borderColor": "#fff",
                },
                "data": close_price,
            },
        ],
    }


def export_png(result_df: pd.DataFrame, output_path: str, stock_code: str = "") -> None:
    dates = result_df["date"].astype(str).tolist()
    vpu_up = result_df["vpu_up"].values
    vpu_down = result_df["vpu_down"].abs().values
    ma5 = result_df["ma5"].values
    close_price = result_df["close_price"].values

    x = np.arange(len(dates))

    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx()

    ax1.bar(x, vpu_up, color="#eb5454", alpha=0.8, label="VPU_Up (抛压)")
    ax1.bar(x, -vpu_down, color="#47b262", alpha=0.8, label="VPU_Down (支撑)")
    ax1.plot(x, ma5, color="#e6a23c", linewidth=2.5, label="MA5", zorder=5)
    ax1.axhline(0, color="#aaa", linewidth=0.8)

    ax2.plot(
        x,
        close_price,
        color="#333333",
        linewidth=2,
        linestyle="--",
        label="收盘价",
        zorder=4,
    )

    tick_step = max(1, len(dates) // 20)
    ax1.set_xticks(x[::tick_step])
    ax1.set_xticklabels(dates[::tick_step], rotation=45, ha="right", fontsize=8)
    ax1.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{abs(int(v)):,}")
    )

    ax1.set_ylabel("VPU (手/0.05元)", color="#333")
    ax2.set_ylabel("收盘价 (元)", color="#333")

    title = f"VPU 流动性深度指标 — {stock_code}" if stock_code else "VPU 流动性深度指标"
    ax1.set_title(title, fontsize=14, pad=12)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left", framealpha=0.9)

    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def export_csv(result_df: pd.DataFrame, output_path: str) -> None:
    columns = [
        "date",
        "vpu",
        "vpu_up",
        "vpu_down",
        "apu",
        "ma5",
        "ma10",
        "close_price",
        "is_limit_up",
        "is_limit_down",
        "is_ex_dividend",
    ]
    export_cols = [col for col in columns if col in result_df.columns]
    result_df[export_cols].to_csv(output_path, index=False)
