import streamlit as st
import threading
import queue
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自定义 CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .report-section {
        background: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .decision-buy    { color: #28a745; font-size: 1.8rem; font-weight: 700; }
    .decision-sell   { color: #dc3545; font-size: 1.8rem; font-weight: 700; }
    .decision-hold   { color: #ffc107; font-size: 1.8rem; font-weight: 700; }
    .decision-other  { color: #6c757d; font-size: 1.8rem; font-weight: 700; }
    .stProgress > div > div { background-color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏配置 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 分析配置")
    st.markdown("---")

    ticker = st.text_input(
        "股票代码",
        value="AAPL",
        placeholder="如 AAPL、NVDA、TSLA",
        help="支持美股代码（yfinance 数据源）"
    ).upper().strip()

    analysis_date = st.date_input(
        "分析日期",
        value=datetime.date.today() - datetime.timedelta(days=1),
        max_value=datetime.date.today() - datetime.timedelta(days=1),
        help="选择要分析的交易日期"
    )

    st.markdown("### 🤖 模型配置")
    llm_provider = st.selectbox(
        "LLM 提供商",
        options=["openrouter", "openai", "anthropic", "google"],
        index=0,
    )

    # 根据提供商显示不同的模型选项
    model_options = {
        "openrouter": [
            "anthropic/claude-opus-4.6",
            "anthropic/claude-sonnet-4-5",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash-001",
            "deepseek/deepseek-chat-v3-0324",
            "meta-llama/llama-4-maverick",
        ],
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "anthropic": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-3-5-sonnet-20241022"],
        "google": ["gemini-2.0-flash", "gemini-1.5-pro"],
    }

    deep_think_model = st.selectbox(
        "深度思考模型（主分析）",
        options=model_options.get(llm_provider, []),
        index=0,
        help="用于深度分析的主力模型，消耗 Token 较多"
    )

    quick_think_model = st.selectbox(
        "快速思考模型（辅助）",
        options=model_options.get(llm_provider, []),
        index=min(1, len(model_options.get(llm_provider, [])) - 1),
        help="用于快速判断的辅助模型"
    )

    st.markdown("### 🔬 分析深度")
    max_debate_rounds = st.slider(
        "多空辩论轮数",
        min_value=1, max_value=3, value=1,
        help="轮数越多分析越深入，但耗时越长"
    )

    max_risk_rounds = st.slider(
        "风险讨论轮数",
        min_value=1, max_value=3, value=1,
    )

    st.markdown("---")
    st.markdown("### 🔑 API Key")

    # 检测环境变量中是否已有 Key
    env_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if env_key:
        st.success("✅ 已从环境变量读取 API Key")
        api_key_input = ""
    else:
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
        )

    st.markdown("---")
    analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

# ── 主界面 ────────────────────────────────────────────────
st.markdown('<div class="main-header">📈 TradingAgents</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agents LLM Financial Trading Framework · 多智能体 LLM 金融交易分析</div>', unsafe_allow_html=True)

# 功能介绍
if not analyze_btn:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("🔍 **基本面分析**\n\n财务报表、估值指标、行业对比")
    with col2:
        st.info("📊 **技术面分析**\n\n均线、RSI、MACD、成交量")
    with col3:
        st.info("📰 **情绪分析**\n\n新闻资讯、市场情绪、社交媒体")
    with col4:
        st.info("⚖️ **多空辩论**\n\n多方/空方 Agent 辩论，风险评估")

# ── 执行分析 ──────────────────────────────────────────────
if analyze_btn:
    if not ticker:
        st.error("请输入股票代码！")
        st.stop()

    # 设置 API Key
    final_api_key = api_key_input or env_key
    if not final_api_key:
        st.error("请输入 API Key 或在环境变量中配置！")
        st.stop()

    # 设置环境变量
    if llm_provider == "openrouter":
        os.environ["OPENROUTER_API_KEY"] = final_api_key
    elif llm_provider == "openai":
        os.environ["OPENAI_API_KEY"] = final_api_key
    elif llm_provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = final_api_key
    elif llm_provider == "google":
        os.environ["GOOGLE_API_KEY"] = final_api_key

    st.markdown(f"## 📋 {ticker} · {analysis_date} 分析报告")
    st.markdown("---")

    # 进度展示
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    log_placeholder = st.empty()

    log_messages = []

    def update_progress(step, total, message):
        progress_placeholder.progress(step / total, text=f"步骤 {step}/{total}")
        status_placeholder.info(f"🔄 {message}")
        log_messages.append(f"✔ {message}")
        log_placeholder.markdown("\n".join(log_messages[-8:]))

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        update_progress(1, 7, "初始化分析引擎...")

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = llm_provider
        config["deep_think_llm"] = deep_think_model
        config["quick_think_llm"] = quick_think_model
        config["max_debate_rounds"] = max_debate_rounds
        config["max_risk_discuss_rounds"] = max_risk_rounds

        # OpenRouter 特殊配置
        if llm_provider == "openrouter":
            config["backend_url"] = "https://openrouter.ai/api/v1"
            config["llm_provider"] = "openai"  # LiteLLM 兼容模式
            os.environ["OPENAI_API_KEY"] = final_api_key
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

        update_progress(2, 7, "加载数据源配置...")

        config["data_vendors"] = {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "yfinance",
            "news_data": "yfinance",
        }

        update_progress(3, 7, f"连接市场数据，获取 {ticker} 行情...")

        ta = TradingAgentsGraph(debug=False, config=config)

        update_progress(4, 7, "多 Agent 协同分析中（基本面、技术面、情绪）...")

        trade_date_str = analysis_date.strftime("%Y-%m-%d")
        final_state, decision = ta.propagate(ticker, trade_date_str)

        update_progress(5, 7, "多空辩论与风险评估中...")
        update_progress(6, 7, "生成最终交易决策...")
        update_progress(7, 7, "分析完成！")

        progress_placeholder.empty()
        status_placeholder.empty()
        log_placeholder.empty()

        # ── 展示结果 ──────────────────────────────────────
        # 决策卡片
        decision_upper = str(decision).upper()
        if "BUY" in decision_upper:
            decision_class = "decision-buy"
            decision_emoji = "🟢 买入 (BUY)"
        elif "SELL" in decision_upper:
            decision_class = "decision-sell"
            decision_emoji = "🔴 卖出 (SELL)"
        elif "HOLD" in decision_upper:
            decision_class = "decision-hold"
            decision_emoji = "🟡 持有 (HOLD)"
        else:
            decision_class = "decision-other"
            decision_emoji = f"⚪ {decision}"

        col_dec, col_info = st.columns([1, 2])
        with col_dec:
            st.markdown("### 🎯 最终决策")
            st.markdown(f'<div class="{decision_class}">{decision_emoji}</div>', unsafe_allow_html=True)
        with col_info:
            st.markdown("### 📌 分析参数")
            st.markdown(f"""
| 参数 | 值 |
|------|-----|
| 股票代码 | `{ticker}` |
| 分析日期 | `{trade_date_str}` |
| 深度模型 | `{deep_think_model}` |
| 快速模型 | `{quick_think_model}` |
| 辩论轮数 | `{max_debate_rounds}` |
""")

        st.markdown("---")

        # 各 Agent 报告
        tabs = st.tabs(["📊 技术面", "📰 新闻情绪", "💹 基本面", "⚔️ 多空辩论", "⚖️ 风险评估", "📝 交易计划", "🔍 完整决策"])

        with tabs[0]:
            st.markdown("### 技术面分析报告")
            market_report = final_state.get("market_report", "暂无数据")
            st.markdown(f'<div class="report-section">{market_report}</div>', unsafe_allow_html=True)

        with tabs[1]:
            st.markdown("### 新闻与情绪分析")
            col_news, col_sent = st.columns(2)
            with col_news:
                st.markdown("**📰 新闻报告**")
                st.markdown(final_state.get("news_report", "暂无数据"))
            with col_sent:
                st.markdown("**💬 情绪报告**")
                st.markdown(final_state.get("sentiment_report", "暂无数据"))

        with tabs[2]:
            st.markdown("### 基本面分析报告")
            st.markdown(final_state.get("fundamentals_report", "暂无数据"))

        with tabs[3]:
            st.markdown("### 多空辩论记录")
            debate_state = final_state.get("investment_debate_state", {})
            col_bull, col_bear = st.columns(2)
            with col_bull:
                st.markdown("**🐂 多方观点**")
                bull_history = debate_state.get("bull_history", "暂无数据")
                st.markdown(bull_history if bull_history else "暂无数据")
            with col_bear:
                st.markdown("**🐻 空方观点**")
                bear_history = debate_state.get("bear_history", "暂无数据")
                st.markdown(bear_history if bear_history else "暂无数据")
            st.markdown("**⚖️ 裁判决策**")
            st.markdown(debate_state.get("judge_decision", "暂无数据"))

        with tabs[4]:
            st.markdown("### 风险评估报告")
            risk_state = final_state.get("risk_debate_state", {})
            col_agg, col_con, col_neu = st.columns(3)
            with col_agg:
                st.markdown("**⚡ 激进派**")
                st.markdown(risk_state.get("aggressive_history", "暂无数据") or "暂无数据")
            with col_con:
                st.markdown("**🛡️ 保守派**")
                st.markdown(risk_state.get("conservative_history", "暂无数据") or "暂无数据")
            with col_neu:
                st.markdown("**🎯 中立派**")
                st.markdown(risk_state.get("neutral_history", "暂无数据") or "暂无数据")
            st.markdown("**📋 风险裁决**")
            st.markdown(risk_state.get("judge_decision", "暂无数据") or "暂无数据")

        with tabs[5]:
            st.markdown("### 交易计划")
            st.markdown(final_state.get("investment_plan", "暂无数据"))
            st.markdown("**📋 Trader 决策**")
            st.markdown(final_state.get("trader_investment_plan", "暂无数据"))

        with tabs[6]:
            st.markdown("### 完整最终决策")
            st.markdown(final_state.get("final_trade_decision", "暂无数据"))

        st.success(f"✅ {ticker} 分析完成！最终决策：**{decision}**")

    except ImportError as e:
        st.error(f"模块导入失败：{e}\n请确认依赖已正确安装。")
    except Exception as e:
        st.error(f"分析过程中出错：{str(e)}")
        with st.expander("查看详细错误信息"):
            import traceback
            st.code(traceback.format_exc())

# ── 页脚 ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#999; font-size:0.85rem;'>"
    "TradingAgents · Multi-Agents LLM Financial Trading Framework · "
    "<a href='https://github.com/TauricResearch/TradingAgents' target='_blank'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
