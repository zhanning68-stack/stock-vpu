import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
    ma10 = result_df["ma10"].tolist()

    # Candlestick data: [open, close, low, high]
    kline_data = result_df[["open", "close", "low", "high"]].values.tolist()

    title_text = f"VPU 深度分析 — {stock_code}" if stock_code else "VPU 深度分析"

    tooltip_formatter = (
        "function(params) {"
        "  var date = params[0].axisValue;"
        "  var html = '<b>' + date + '</b><br/>';"
        "  params.forEach(function(p) {"
        "    var val = p.value;"
        "    if (p.seriesName === 'VPU_Down') val = Math.abs(val);"
        "    if (p.seriesName === 'K线') {"
        "        var o = val[1], c = val[2], l = val[3], h = val[4];"
        "        html += p.marker + ' 开: ' + o + ' 收: ' + c + ' 低: ' + l + ' 高: ' + h + '<br/>';"
        "    } else {"
        "        var display = (val !== null && val !== undefined) ? val.toLocaleString() + (p.seriesName.includes('VPU') ? ' 手' : '') : '-';"
        "        html += p.marker + ' ' + p.seriesName + ': ' + display + '<br/>';"
        "    }"
        "  });"
        "  return html;"
        "}"
    )

    yaxis_label_formatter = "function(value) { return Math.abs(value).toLocaleString(); }"

    return {
        "backgroundColor": "transparent",
        "title": {
            "text": title_text,
            "left": "center",
            "textStyle": {"color": "#e0e0e0", "fontSize": 20, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": tooltip_formatter,
            "backgroundColor": "rgba(20,20,30,0.9)",
            "borderColor": "#333",
            "textStyle": {"color": "#e0e0e0"},
        },
        "legend": {
            "data": ["K线", "MA5", "MA10", "VPU_Up", "VPU_Down"],
            "top": 35,
            "textStyle": {"color": "#aaa"},
        },
        "axisPointer": {
            "link": [{"xAxisIndex": "all"}],
            "label": {"backgroundColor": "#555"},
        },
        "grid": [
            {"left": "10%", "right": "8%", "height": "50%", "top": "15%"},
            {"left": "10%", "right": "8%", "top": "70%", "height": "20%"},
        ],
        "xAxis": [
            {
                "type": "category",
                "data": dates,
                "boundaryGap": True,
                "axisLine": {"onZero": False},
                "splitLine": {"show": False},
                "min": "dataMin",
                "max": "dataMax",
                "axisPointer": {"z": 100},
                "axisLabel": {"color": "#aaa"},
            },
            {
                "type": "category",
                "gridIndex": 1,
                "data": dates,
                "boundaryGap": True,
                "axisLine": {"onZero": False},
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "min": "dataMin",
                "max": "dataMax",
            },
        ],
        "yAxis": [
            {
                "scale": True,
                "name": "价格 (元)",
                "axisLabel": {"color": "#aaa"},
                "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.06)", "type": "dashed"}},
            },
            {
                "scale": True,
                "gridIndex": 1,
                "splitNumber": 2,
                "axisLabel": {
                    "show": True,
                    "formatter": yaxis_label_formatter,
                    "color": "#aaa",
                },
                "axisLine": {"show": False},
                "axisTick": {"show": False},
                "splitLine": {
                    "show": True,
                    "lineStyle": {"type": "dashed", "color": "rgba(255,255,255,0.06)"},
                },
                "name": "VPU (手/0.05元)",
                "nameLocation": "middle",
                "nameGap": 40,
            },
        ],
        "dataZoom": [
            {"type": "inside", "xAxisIndex": [0, 1], "start": 50, "end": 100},
            {
                "show": True,
                "xAxisIndex": [0, 1],
                "type": "slider",
                "top": "92%",
                "start": 50,
                "end": 100,
                "backgroundColor": "rgba(255,255,255,0.05)",
                "dataBackground": {
                    "lineStyle": {"color": "#555"},
                    "areaStyle": {"color": "rgba(255,255,255,0.1)"},
                },
            },
        ],
        "series": [
            {
                "name": "K线",
                "type": "candlestick",
                "data": kline_data,
                "itemStyle": {
                    "color": "#ff4b4b",
                    "color0": "#00c878",
                    "borderColor": "#ff4b4b",
                    "borderColor0": "#00c878",
                },
            },
            {
                "name": "MA5",
                "type": "line",
                "data": ma5,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"opacity": 0.8, "color": "#e6a23c", "width": 2},
            },
            {
                "name": "MA10",
                "type": "line",
                "data": ma10,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"opacity": 0.8, "color": "#409eff", "width": 2},
            },
            {
                "name": "VPU_Up",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "stack": "Total",
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(255, 75, 75, 0.7)"},
                            {"offset": 1, "color": "rgba(255, 75, 75, 0.15)"},
                        ],
                    },
                    "borderRadius": [4, 4, 0, 0],
                },
                "data": vpu_up,
            },
            {
                "name": "VPU_Down",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "stack": "Total",
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(0, 200, 120, 0.15)"},
                            {"offset": 1, "color": "rgba(0, 200, 120, 0.7)"},
                        ],
                    },
                    "borderRadius": [0, 0, 4, 4],
                },
                "data": vpu_down,
            },
        ],
    }


def render_apu_chart(result_df: pd.DataFrame, stock_code: str = "") -> dict:
    dates = result_df["date"].astype(str).tolist()
    apu = result_df["apu"].tolist()
    close_price = result_df["close_price"].tolist()

    title_text = f"APU 成交额深度指标 — {stock_code}" if stock_code else "APU 成交额深度指标"

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
        "backgroundColor": "transparent",
        "title": {
            "text": title_text,
            "textStyle": {"color": "#e0e0e0", "fontSize": 18},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": tooltip_formatter,
            "backgroundColor": "rgba(20,20,30,0.9)",
            "borderColor": "#333",
            "textStyle": {"color": "#e0e0e0"},
        },
        "legend": {
            "data": ["APU (成交额)", "收盘价"],
            "top": 40,
            "textStyle": {"color": "#aaa"},
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
                "axisLabel": {"color": "#aaa"},
            }
        ],
        "yAxis": [
            {
                "type": "value",
                "name": "APU (元/0.05元)",
                "position": "left",
                "axisLabel": {"color": "#aaa"},
                "splitLine": {"lineStyle": {"type": "dashed", "color": "rgba(255,255,255,0.06)"}},
            },
            {
                "type": "value",
                "name": "收盘价 (元)",
                "position": "right",
                "axisLabel": {"color": "#aaa"},
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
                "itemStyle": {"color": "#409eff", "opacity": 0.7},
                "data": apu,
            },
            {
                "name": "收盘价",
                "type": "line",
                "yAxisIndex": 1,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": "#e0e0e0", "width": 2, "type": "dashed"},
                "itemStyle": {
                    "color": "#e0e0e0",
                    "borderWidth": 2,
                    "borderColor": "#333",
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
    ma10 = result_df["ma10"].values

    # [open, close, low, high]
    opens = result_df["open"].values
    closes = result_df["close"].values
    highs = result_df["high"].values
    lows = result_df["low"].values

    x = np.arange(len(dates))

    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1]}, sharex=True)

    # Plot Candlestick on ax1
    # Use rectangles for candle bodies
    for i in range(len(x)):
        color = "#ef5350" if closes[i] >= opens[i] else "#26a69a"
        # Wick
        ax1.vlines(x[i], lows[i], highs[i], color=color, linewidth=1)
        # Body
        lower = min(opens[i], closes[i])
        height = abs(opens[i] - closes[i])
        if height == 0:
            height = 0.01  # visualization fix
        rect = patches.Rectangle((x[i] - 0.3, lower), 0.6, height, color=color)
        ax1.add_patch(rect)

    ax1.plot(x, ma5, color="#e6a23c", linewidth=1.5, label="MA5", alpha=0.7)
    ax1.plot(x, ma10, color="#2f4554", linewidth=1.5, label="MA10", alpha=0.7)

    ax1.set_ylabel("价格 (元)")
    title = f"VPU 深度分析 — {stock_code}" if stock_code else "VPU 深度分析"
    ax1.set_title(title, fontsize=14)
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    # Plot VPU on ax3
    ax3.bar(x, vpu_up, color="#ef5350", alpha=0.6, label="VPU_Up")
    ax3.bar(x, -vpu_down, color="#26a69a", alpha=0.6, label="VPU_Down")
    ax3.axhline(0, color="black", linewidth=0.5)

    ax3.set_ylabel("VPU (手)")
    ax3.legend(loc="upper left")
    ax3.grid(alpha=0.3)

    tick_step = max(1, len(dates) // 15)
    ax3.set_xticks(x[::tick_step])
    ax3.set_xticklabels(dates[::tick_step], rotation=45, ha="right")

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
