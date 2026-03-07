import sys
import os
from datetime import date, timedelta

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts, JsCode

sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from data_fetcher import fetch_5min_kline
from calculator import calculate_vpu
from visualizer import render_chart, render_apu_chart

st.set_page_config(
    page_title="VPU 流动性深度分析",
    page_icon="📊",
    layout="wide",
)


def wrap_js_code(obj):
    if isinstance(obj, dict):
        return {k: wrap_js_code(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [wrap_js_code(item) for item in obj]
    elif isinstance(obj, str) and obj.strip().startswith("function"):
        return JsCode(obj)
    return obj


st.sidebar.title("参数设置")

stock_code = st.sidebar.text_input("股票代码", value="600519")

today = date.today()
default_start = today - timedelta(days=30)

start_date = st.sidebar.date_input("开始日期", value=default_start)
end_date = st.sidebar.date_input("结束日期", value=today)

price_unit = st.sidebar.slider("PRICE_UNIT (最小价差单位)", 0.01, 0.10, 0.05, 0.01)
trim_ratio = st.sidebar.slider("TRIM_RATIO (截尾比例)", 0.0, 0.40, 0.25, 0.05)
min_price_spread = st.sidebar.slider(
    "MIN_PRICE_SPREAD (最小有效价差)", 0.01, 0.10, 0.03, 0.01
)

skip_first_last = st.sidebar.checkbox("跳过首尾5分钟", value=True)
enable_direction = st.sidebar.checkbox("计算方向性指标", value=True)

fetch_button = st.sidebar.button("获取数据并计算", type="primary")

st.title("VPU 流动性深度分析")

if fetch_button:
    if not stock_code.strip():
        st.error("请输入有效的股票代码")
    elif start_date >= end_date:
        st.error("开始日期必须早于结束日期")
    else:
        cfg = Config(
            PRICE_UNIT=price_unit,
            TRIM_RATIO=trim_ratio,
            MIN_PRICE_SPREAD=min_price_spread,
            SKIP_FIRST_LAST=skip_first_last,
            ENABLE_DIRECTION=enable_direction,
        )

        with st.spinner("正在获取数据..."):
            try:
                raw_df = fetch_5min_kline(
                    stock_code.strip(),
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )

                if raw_df.empty:
                    st.error(
                        f"未获取到股票 {stock_code} 的数据，请检查股票代码或日期范围"
                    )
                    st.session_state.pop("result_df", None)
                    st.session_state.pop("stock_code", None)
                else:
                    result_df = calculate_vpu(raw_df, cfg, code=stock_code.strip())

                    if result_df.empty:
                        st.error("计算结果为空，请尝试扩大日期范围或调整参数")
                        st.session_state.pop("result_df", None)
                        st.session_state.pop("stock_code", None)
                    else:
                        st.session_state["result_df"] = result_df
                        st.session_state["stock_code"] = stock_code.strip()
                        st.success(f"成功获取 {len(result_df)} 个交易日的数据")

            except Exception as e:
                st.error(f"数据获取失败：{str(e)}")
                st.session_state.pop("result_df", None)
                st.session_state.pop("stock_code", None)

if "result_df" in st.session_state and "stock_code" in st.session_state:
    result_df = st.session_state["result_df"]
    code = st.session_state["stock_code"]

    avg_vpu = result_df["vpu"].mean()
    avg_vpu_up = result_df["vpu_up"].mean()
    avg_vpu_down = result_df["vpu_down"].mean()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="平均 VPU",
            value=f"{avg_vpu:,.0f} 手" if not pd.isna(avg_vpu) else "N/A",
        )

    with col2:
        st.metric(
            label="平均 VPU_Up (抛压)",
            value=f"{avg_vpu_up:,.0f} 手" if not pd.isna(avg_vpu_up) else "N/A",
        )

    with col3:
        st.metric(
            label="平均 VPU_Down (支撑)",
            value=f"{avg_vpu_down:,.0f} 手" if not pd.isna(avg_vpu_down) else "N/A",
        )

    st.divider()

    tab1, tab2 = st.tabs(["VPU 指标", "APU 指标"])

    with tab1:
        option = render_chart(result_df, stock_code=code)
        option = wrap_js_code(option)
        st_echarts(option, height="500px")

    with tab2:
        apu_option = render_apu_chart(result_df, stock_code=code)
        apu_option = wrap_js_code(apu_option)
        st_echarts(apu_option, height="500px")

    st.divider()

    csv_buffer = result_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 导出 CSV 数据",
        data=csv_buffer,
        file_name=f"VPU_{code}_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

else:
    st.info("请在左侧设置参数后点击「获取数据并计算」按钮")
