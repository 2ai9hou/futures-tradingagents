"""
TradingAgents Web Interface
基于 Streamlit 的多智能体期货辩论系统交互界面
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

load_dotenv()


FUTURES_SYMBOLS = {
    "螺纹钢 (rb)": "rb",
    "热轧卷板 (hc)": "hc",
    "铁矿石 (i)": "i",
    "焦煤 (jm)": "jm",
    "焦炭 (j)": "j",
    "豆粕 (m)": "m",
    "豆油 (y)": "y",
    "棕榈油 (p)": "p",
    "黄金 (au)": "au",
    "白银 (ag)": "ag",
    "铜 (cu)": "cu",
    "铝 (al)": "al",
    "锌 (zn)": "zn",
    "原油 (sc)": "sc",
    "沥青 (bu)": "bu",
}

TIME_PERIODS = {
    "日线": 30,
    "周线": 70,
    "月线": 180,
}


def init_session_state():
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "kline_data" not in st.session_state:
        st.session_state.kline_data = None
    if "indicator_data" not in st.session_state:
        st.session_state.indicator_data = None
    if "basis_data" not in st.session_state:
        st.session_state.basis_data = None
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    if "error_message" not in st.session_state:
        st.session_state.error_message = None


@st.cache_data(ttl=3600)
def try_fetch_kline_data(symbol: str, days: int):
    try:
        import akshare as ak
        from tradingagents.dataflows.akshare_futures import get_main_contract_code

        main_contract = get_main_contract_code(symbol)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        df = ak.futures_zh_daily_sina(symbol=main_contract)
        if df is None or df.empty:
            return None

        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        col_mapping = {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "hold": "open_interest",
        }
        df = df.rename(columns=col_mapping)

        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        df = df.sort_values("date")

        return df
    except Exception as e:
        st.warning(f"K线数据获取失败: {str(e)}")
        return None


def calculate_technical_indicators(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    try:
        result = df.copy()

        close = pd.to_numeric(result["close"], errors="coerce")

        result["sma_5"] = close.rolling(window=5).mean()
        result["sma_10"] = close.rolling(window=10).mean()
        result["sma_20"] = close.rolling(window=20).mean()

        result["ema_12"] = close.ewm(span=12, adjust=False).mean()
        result["ema_26"] = close.ewm(span=26, adjust=False).mean()

        result["macd"] = result["ema_12"] - result["ema_26"]
        result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
        result["macd_hist"] = result["macd"] - result["macd_signal"]

        close_20 = close.rolling(window=20).mean()
        std_20 = close.rolling(window=20).std()
        result["boll_upper"] = close_20 + (std_20 * 2)
        result["boll_middle"] = close_20
        result["boll_lower"] = close_20 - (std_20 * 2)

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        result["rsi"] = 100 - (100 / (1 + rs))

        return result
    except Exception as e:
        st.warning(f"技术指标计算失败: {str(e)}")
        return df


@st.cache_data(ttl=3600)
def try_fetch_basis_data(symbol: str):
    try:
        import akshare as ak
        from tradingagents.dataflows.akshare_futures import get_main_contract_code

        main_contract = get_main_contract_code(symbol)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        df = ak.get_futures_daily_sn(symbol=main_contract, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return None

        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        return df
    except Exception as e:
        st.warning(f"基差数据获取失败: {str(e)}")
        return None


def plot_kline_chart(df: pd.DataFrame, indicator_df: pd.DataFrame):
    if df is None or df.empty:
        st.warning("暂无K线数据")
        return None

    try:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.5, 0.25, 0.25],
            subplot_titles=("K线图", "成交量", "MACD & RSI"),
        )

        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K线",
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
            ),
            row=1,
            col=1,
        )

        if indicator_df is not None and "sma_5" in indicator_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["sma_5"],
                    mode="lines",
                    name="SMA5",
                    line=dict(color="#FF6B6B", width=1),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["sma_10"],
                    mode="lines",
                    name="SMA10",
                    line=dict(color="#4ECDC4", width=1),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["sma_20"],
                    mode="lines",
                    name="SMA20",
                    line=dict(color="#FFE66D", width=1),
                ),
                row=1,
                col=1,
            )

        if "boll_upper" in indicator_df.columns and indicator_df is not None:
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["boll_upper"],
                    mode="lines",
                    name="布林上轨",
                    line=dict(color="rgba(150,150,150,0.5)", width=1),
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["boll_lower"],
                    mode="lines",
                    name="布林下轨",
                    line=dict(color="rgba(150,150,150,0.5)", width=1),
                    fill="tonexty",
                    fillcolor="rgba(150,150,150,0.1)",
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color="#5461c8",
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

        if indicator_df is not None and "macd" in indicator_df.columns:
            colors = ["#26a69a" if val >= 0 else "#ef5350" for val in indicator_df["macd_hist"]]
            fig.add_trace(
                go.Bar(
                    x=indicator_df["date"],
                    y=indicator_df["macd_hist"],
                    name="MACD柱",
                    marker_color=colors,
                ),
                row=3,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["macd"],
                    mode="lines",
                    name="MACD",
                    line=dict(color="#2196F3", width=1.5),
                ),
                row=3,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["macd_signal"],
                    mode="lines",
                    name="Signal",
                    line=dict(color="#FF9800", width=1.5),
                ),
                row=3,
                col=1,
            )

        if indicator_df is not None and "rsi" in indicator_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=indicator_df["date"],
                    y=indicator_df["rsi"],
                    mode="lines",
                    name="RSI",
                    line=dict(color="#9C27B0", width=1.5),
                ),
                row=3,
                col=1,
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5)

        fig.update_layout(
            height=700,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_dark",
            xaxis=dict(rangeslider=dict(visible=False)),
        )

        return fig
    except Exception as e:
        st.error(f"图表绘制失败: {str(e)}")
        return None


def plot_basis_chart(basis_df: pd.DataFrame, symbol: str):
    if basis_df is None or basis_df.empty:
        return None

    try:
        if "收盘价" in basis_df.columns or "收盘" in basis_df.columns:
            price_col = "收盘价" if "收盘价" in basis_df.columns else "收盘"
        else:
            return None

        basis_values = []
        dates = []

        for idx, row in basis_df.iterrows():
            try:
                spot_response = try_fetch_basis_data(symbol)
                if spot_response is not None and not spot_response.empty:
                    if "收盘价" in spot_response.columns:
                        spot_price = float(spot_response.iloc[-1]["收盘价"])
                    else:
                        spot_price = 4000
                else:
                    spot_price = 4000

                fut_price = float(row[price_col])
                basis_val = spot_price - fut_price
                basis_values.append(basis_val)

                if "date" in basis_df.columns:
                    dates.append(row["date"])
                else:
                    dates.append(idx)
            except Exception:
                continue

        if not basis_values:
            return None

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=basis_values,
                mode="lines+markers",
                name="基差 (现货-期货)",
                line=dict(color="#00BCD4", width=2),
                marker=dict(size=6),
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)

        fig.update_layout(
            title=f"{symbol.upper()} 基差图",
            height=300,
            template="plotly_dark",
            yaxis_title="基差值",
            showlegend=True,
        )

        return fig
    except Exception as e:
        st.warning(f"基差图绘制失败: {str(e)}")
        return None


def run_trading_analysis(symbol: str, trade_date: str, selected_analysts: list, agent_weights: dict):
    try:
        config = DEFAULT_CONFIG.copy()

        config["deep_think_llm"] = "gpt-5.4-mini"
        config["quick_think_llm"] = "gpt-5.4-mini"
        config["max_debate_rounds"] = 1
        config["output_language"] = "Chinese"

        config["data_vendors"] = {
            "core_stock_apis": "akshare",
            "technical_indicators": "akshare",
            "fundamental_data": "akshare",
            "news_data": "akshare",
        }

        ta = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=config,
        )

        _, decision = ta.propagate(symbol, trade_date)

        return {
            "success": True,
            "decision": decision,
            "state": ta.curr_state,
        }
    except Exception as e:
        error_msg = f"分析过程出错: {str(e)}"
        st.error(error_msg)
        st.text(traceback.format_exc())
        return {
            "success": False,
            "error": error_msg,
        }


def render_analyst_report(state: dict, analyst_name: str, report_key: str):
    try:
        report = state.get(report_key, "暂无报告数据")
        if not report or report.strip() == "":
            report = "暂无报告数据"

        st.markdown(f"### {analyst_name}")
        st.info(report[:2000] + "..." if len(report) > 2000 else report)
    except Exception as e:
        st.warning(f"渲染{analyst_name}报告失败: {str(e)}")


def render_debate_section(state: dict):
    try:
        st.markdown("---")
        st.markdown("## 辩论过程")

        if "risk_debate_state" not in state:
            st.warning("暂无辩论数据")
            return

        risk_state = state["risk_debate_state"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 激进派观点")
            aggressive = risk_state.get("aggressive_history", "暂无")
            st.error(aggressive[:1500] + "..." if len(aggressive) > 1500 else aggressive)

        with col2:
            st.markdown("### 保守派观点")
            conservative = risk_state.get("conservative_history", "暂无")
            st.warning(conservative[:1500] + "..." if len(conservative) > 1500 else conservative)

        st.markdown("### 中性派观点")
        neutral = risk_state.get("neutral_history", "暂无")
        st.info(neutral[:1500] + "..." if len(neutral) > 1500 else neutral)

        st.markdown("### 投资研究团队辩论")
        invest_state = state.get("investment_debate_state", {})
        bull_history = invest_state.get("bull_history", "暂无")
        bear_history = invest_state.get("bear_history", "暂无")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**多头观点**")
            st.success(bull_history[:1000] + "..." if len(bull_history) > 1000 else bull_history)
        with c2:
            st.markdown("**空头观点**")
            st.error(bear_history[:1000] + "..." if len(bear_history) > 1000 else bear_history)

    except Exception as e:
        st.error(f"渲染辩论部分失败: {str(e)}")


def render_final_decision(state: dict, decision: str):
    try:
        st.markdown("---")
        st.markdown("## 最终交易指令")

        st.markdown("### 风险评级与决策")
        st.success(decision)

        st.markdown("### 交易计划详情")
        investment_plan = state.get("investment_plan", "暂无")
        if investment_plan:
            st.markdown(investment_plan[:2000] + "..." if len(investment_plan) > 2000 else investment_plan)

        trader_plan = state.get("trader_investment_plan", "暂无")
        if trader_plan:
            st.markdown("### 交易员提案")
            st.info(trader_plan[:1500] + "..." if len(trader_plan) > 1500 else trader_plan)

    except Exception as e:
        st.error(f"渲染最终决策失败: {str(e)}")


def main():
    st.set_page_config(
        page_title="TradingAgents 智能交易系统",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    st.title("📈 TradingAgents 多智能体期货分析系统")

    with st.sidebar:
        st.header("配置面板")

        symbol_display = st.selectbox("期货品种", options=list(FUTURES_SYMBOLS.keys()), index=0)
        symbol = FUTURES_SYMBOLS[symbol_display]

        period_display = st.selectbox("时间周期", options=list(TIME_PERIODS.keys()), index=0)
        days = TIME_PERIODS[period_display]

        trade_date = st.date_input(
            "交易日期",
            value=datetime.now() - timedelta(days=1),
            max_value=datetime.now(),
        ).strftime("%Y-%m-%d")

        st.markdown("---")
        st.markdown("### Agent 权重配置")

        st.markdown("**基本面权重**")
        fundamental_weight = st.slider(
            "基本面分析权重",
            min_value=0,
            max_value=100,
            value=50,
            step=10,
            help="调节基本面分析师的权重",
        )

        st.markdown("**技术面权重**")
        technical_weight = st.slider(
            "技术分析权重",
            min_value=0,
            max_value=100,
            value=50,
            step=10,
            help="调节技术分析师的权重",
        )

        if fundamental_weight + technical_weight > 0:
            total = fundamental_weight + technical_weight
            fund_ratio = fundamental_weight / total
            tech_ratio = technical_weight / total
        else:
            fund_ratio = 0.5
            tech_ratio = 0.5

        st.caption(f"基本面: {fund_ratio:.0%} | 技术面: {tech_ratio:.0%}")

        st.markdown("---")
        st.markdown("### 分析师团队")

        use_market = st.checkbox("市场分析师", value=True)
        use_fundamental = st.checkbox("基本面分析师", value=True)
        use_news = st.checkbox("新闻分析师", value=True)
        use_social = st.checkbox("社交媒体分析师", value=True)

        selected_analysts = []
        if use_market:
            selected_analysts.append("market")
        if use_fundamental:
            selected_analysts.append("fundamentals")
        if use_news:
            selected_analysts.append("news")
        if use_social:
            selected_analysts.append("social")

        if not selected_analysts:
            st.warning("请至少选择一个分析师")

        st.markdown("---")

        analyze_button = st.button(
            "🚀 开始分析",
            type="primary",
            disabled=st.session_state.is_running or not selected_analysts,
            use_container_width=True,
        )

        if analyze_button and not st.session_state.is_running:
            st.session_state.is_running = True
            st.session_state.analysis_result = None
            st.session_state.error_message = None

            with st.spinner("正在运行多智能体分析，请稍候..."):
                result = run_trading_analysis(symbol, trade_date, selected_analysts, {
                    "fundamental": fund_ratio,
                    "technical": tech_ratio,
                })

                st.session_state.analysis_result = result
                st.session_state.is_running = False

    tab1, tab2, tab3 = st.tabs(["📊 K线图表", "📋 分析报告", "📝 辩论过程"])

    with tab1:
        col_chart, col_basis = st.columns([3, 1])

        with col_chart:
            if st.session_state.kline_data is None:
                kline_data = try_fetch_kline_data(symbol, days)
                indicator_data = calculate_technical_indicators(kline_data)
                st.session_state.kline_data = kline_data
                st.session_state.indicator_data = indicator_data
            else:
                kline_data = st.session_state.kline_data
                indicator_data = st.session_state.indicator_data

            fig = plot_kline_chart(kline_data, indicator_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无K线数据，请稍后重试")

        with col_basis:
            st.markdown("### 基差图表")
            if st.session_state.basis_data is None:
                basis_df = try_fetch_basis_data(symbol)
                st.session_state.basis_data = basis_df
            else:
                basis_df = st.session_state.basis_data

            basis_fig = plot_basis_chart(basis_df, symbol)
            if basis_fig:
                st.plotly_chart(basis_fig, use_container_width=True)
            else:
                st.info("暂无基差数据")

    with tab2:
        st.markdown("## 分析师报告摘要")

        if st.session_state.analysis_result and st.session_state.analysis_result.get("success"):
            state = st.session_state.analysis_result.get("state")
            if state:
                col1, col2 = st.columns(2)

                with col1:
                    render_analyst_report(state, "市场分析师", "market_report")

                with col2:
                    render_analyst_report(state, "基本面分析师", "fundamentals_report")

                col3, col4 = st.columns(2)

                with col3:
                    render_analyst_report(state, "新闻分析师", "news_report")

                with col4:
                    render_analyst_report(state, "社交媒体分析师", "sentiment_report")
        else:
            st.info("请点击左侧「开始分析」按钮获取分析报告")

    with tab3:
        if st.session_state.analysis_result and st.session_state.analysis_result.get("success"):
            state = st.session_state.analysis_result.get("state")
            decision = st.session_state.analysis_result.get("decision")

            if state:
                render_debate_section(state)
                render_final_decision(state, decision)
        else:
            st.info("请点击左侧「开始分析」按钮获取辩论过程")

            if st.session_state.error_message:
                st.error(st.session_state.error_message)

    if st.session_state.is_running:
        st.markdown("---")
        st.info("⏳ 分析正在进行中，请稍候...")


if __name__ == "__main__":
    main()
