import os
import sys
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

sys.path.insert(0, os.path.dirname(__file__))

from advanced_visualizer import AdvancedVisualizer
from batch_processor import BatchProcessor
from calculator import calculate_vpu
from config import Config, validate_stock_code
from data_fetcher import fetch_5min_kline
from technical_analyzer import TechnicalAnalyzer
from visualizer import render_apu_chart, render_chart, wrap_js_code

st.set_page_config(
    page_title="VPU 流动性深度分析",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
<style>
    [data-testid="stMetric"] {
        background-color: #1e1e2e;
        border: 1px solid #2a2a3e;
        border-radius: 10px;
        padding: 15px 20px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_and_compute_data(code, start, end, cfg_dict):
    raw_df = fetch_5min_kline(code, start, end)
    if raw_df.empty:
        return pd.DataFrame()

    cfg = Config(**cfg_dict)
    result_df = calculate_vpu(raw_df, cfg, code=code)
    return result_df


st.sidebar.title("参数设置")

stock_code = st.sidebar.text_input("股票代码", value="600519")

today = date.today()
default_start = today - timedelta(days=30)

start_date = st.sidebar.date_input("开始日期", value=default_start)
end_date = st.sidebar.date_input("结束日期", value=today)

price_unit = st.sidebar.slider("PRICE_UNIT (最小价差单位)", 0.01, 0.10, 0.05, 0.01)
trim_ratio = st.sidebar.slider("TRIM_RATIO (截尾比例)", 0.0, 0.40, 0.25, 0.05)
min_price_spread = st.sidebar.slider("MIN_PRICE_SPREAD (最小有效价差)", 0.01, 0.10, 0.03, 0.01)

skip_first_last = st.sidebar.checkbox("跳过首尾5分钟", value=True)
enable_direction = st.sidebar.checkbox("计算方向性指标", value=True)

fetch_button = st.sidebar.button("获取数据并计算", type="primary")

st.title("VPU 流动性深度分析")

if fetch_button:
    if not stock_code.strip():
        st.error("请输入有效的股票代码")
        st.session_state.pop("result_df", None)
        st.session_state.pop("stock_code", None)
    elif not validate_stock_code(stock_code.strip()):
        st.error(f"股票代码 '{stock_code}' 格式不正确，支持: 600xxx, 000xxx, 001xxx, 002xxx, 300xxx, 301xxx, 688xxx")
        st.session_state.pop("result_df", None)
        st.session_state.pop("stock_code", None)
    elif start_date >= end_date:
        st.error("开始日期必须早于结束日期")
        st.session_state.pop("result_df", None)
        st.session_state.pop("stock_code", None)
    else:
        cfg = Config(
            PRICE_UNIT=price_unit,
            TRIM_RATIO=trim_ratio,
            MIN_PRICE_SPREAD=min_price_spread,
            SKIP_FIRST_LAST=skip_first_last,
            ENABLE_DIRECTION=enable_direction,
        )

        try:
            result_df = load_and_compute_data(
                stock_code.strip(),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                cfg.__dict__,
            )

            if result_df.empty:
                st.error(f"未获取到股票 {stock_code} 的数据，或计算结果为空")
                st.session_state.pop("result_df", None)
                st.session_state.pop("stock_code", None)
            else:
                st.session_state["result_df"] = result_df
                st.session_state["stock_code"] = stock_code.strip()
                st.success(f"成功获取 {len(result_df)} 个交易日的数据")

        except Exception as e:
            st.error(f"数据获取或计算失败：{e!s}")
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
            help="抛压指标",
        )

    with col3:
        st.metric(
            label="平均 VPU_Down (支撑)",
            value=f"{avg_vpu_down:,.0f} 手" if not pd.isna(avg_vpu_down) else "N/A",
            help="支撑指标",
        )

    st.divider()

    tab1, tab2, tab3 = st.tabs(["VPU 指标", "APU 指标", "对比分析"])

    with tab1:
        st.subheader("VPU 趋势与技术指标")
        show_rsi = st.checkbox("显示 RSI (14)")
        show_bb = st.checkbox("显示布林带 (20, 2)")

        display_df = result_df.copy()
        if show_rsi:
            display_df["rsi"] = TechnicalAnalyzer.calculate_rsi(result_df)
            st.line_chart(display_df.set_index("date")["rsi"])

        option = render_chart(result_df, stock_code=code)
        option = wrap_js_code(option)
        st_echarts(option, height="600px")

    with tab2:
        apu_option = render_apu_chart(result_df, stock_code=code)
        apu_option = wrap_js_code(apu_option)
        st_echarts(apu_option, height="600px")

    with tab3:
        st.subheader("多股票对比")
        compare_codes = st.text_input("输入要对比的股票代码（英文逗号分隔）", value="600519,000858,000568")
        if st.button("开始对比"):
            code_list = [c.strip() for c in compare_codes.split(",") if c.strip()]
            if code_list:
                with st.spinner("正在获取对比数据..."):
                    current_cfg = Config(
                        PRICE_UNIT=price_unit,
                        TRIM_RATIO=trim_ratio,
                        MIN_PRICE_SPREAD=min_price_spread,
                        SKIP_FIRST_LAST=skip_first_last,
                        ENABLE_DIRECTION=enable_direction,
                    )
                    bp = BatchProcessor(current_cfg)
                    batch_results = bp.process_stocks(
                        code_list,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                    )
                    comp_df = bp.get_comparison_df(batch_results, metric="vpu")
                    if not comp_df.empty:
                        c_option = AdvancedVisualizer.render_comparison_chart(comp_df, title="VPU 趋势对比")
                        st_echarts(c_option, height="500px")

                        corr_option = AdvancedVisualizer.render_correlation_matrix(comp_df)
                        st_echarts(corr_option, height="500px")
                    else:
                        st.warning("未能获取足够的对比数据")

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
