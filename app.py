import streamlit as st
import datetime
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI 股票分析平台",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 自定义 CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1f77b4, #2ecc71);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .config-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
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
    .stock-hint {
        font-size: 0.82rem;
        color: #888;
        margin-top: -0.5rem;
        margin-bottom: 0.5rem;
    }
    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 0.3rem;
    }
    .service-card {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        border: 2px solid #dee2e6;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s;
    }
    .service-card:hover {
        border-color: #1f77b4;
        box-shadow: 0 4px 12px rgba(31,119,180,0.15);
    }
    .key-status-ok {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #155724;
        font-size: 0.9rem;
    }
    .key-status-missing {
        background: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #856404;
        font-size: 0.9rem;
    }
    .dsa-iframe-container {
        border: 1px solid #dee2e6;
        border-radius: 12px;
        overflow: hidden;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── 常量 ──────────────────────────────────────────────────
DSA_URL = os.getenv("DSA_SERVICE_URL", "https://stock-server-production-bb12.up.railway.app")

# ── 港股代码自动转换 ──────────────────────────────────────
def normalize_stock_code(raw_code: str) -> str:
    code = raw_code.strip().upper()
    if re.search(r'\.\w{1,2}$', code):
        return code
    if code.isdigit():
        num = int(code)
        if num <= 9999:
            return f"{num:04d}.HK"
        elif len(code) == 6:
            if code.startswith('6'):
                return f"{code}.SS"
            elif code.startswith(('0', '3')):
                return f"{code}.SZ"
            else:
                return code
        else:
            return code
    return code

# ── 模型配置数据 ──────────────────────────────────────────
PROVIDER_MODELS = {
    "openrouter": {
        "label": "OpenRouter（推荐，一个 Key 用所有模型）",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            "anthropic/claude-opus-4.6",
            "anthropic/claude-sonnet-4-5",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-2.5-pro-preview-03-25",
            "google/gemini-2.0-flash-001",
            "deepseek/deepseek-chat-v3-0324",
            "meta-llama/llama-4-maverick",
        ],
    },
    "openai": {
        "label": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    },
    "anthropic": {
        "label": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-3-5-sonnet-20241022"],
    },
    "google": {
        "label": "Google",
        "env_key": "GOOGLE_API_KEY",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
    },
}

# ── Session State 初始化 ──────────────────────────────────
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
if "api_key_saved" not in st.session_state:
    st.session_state.api_key_saved = bool(st.session_state.api_key)

# ══════════════════════════════════════════════════════════
#  顶部标题 + API Key 管理
# ══════════════════════════════════════════════════════════
st.markdown('<div class="main-header">🏦 AI 股票分析平台</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">统一入口 · 每日智能分析 + 多智能体交易决策 · 支持 A股 / 港股 / 美股</div>', unsafe_allow_html=True)

# ── API Key 配置区 ────────────────────────────────────────
with st.expander("🔑 OpenRouter API Key 配置（点击展开）", expanded=not st.session_state.api_key_saved):
    st.markdown("统一管理 API Key，两个分析服务共用同一个 Key。推荐使用 [OpenRouter](https://openrouter.ai/)，一个 Key 即可调用所有主流模型。")

    key_col1, key_col2 = st.columns([4, 1])
    with key_col1:
        new_key = st.text_input(
            "OpenRouter API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="sk-or-v1-...",
            label_visibility="collapsed",
        )
    with key_col2:
        save_key_btn = st.button("💾 保存 Key", use_container_width=True)

    if save_key_btn and new_key:
        st.session_state.api_key = new_key
        st.session_state.api_key_saved = True
        # 同时设置环境变量供 TradingAgents 使用
        os.environ["OPENROUTER_API_KEY"] = new_key
        os.environ["OPENAI_API_KEY"] = new_key
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        st.success("✅ API Key 已保存！两个分析服务均可使用。")
        st.rerun()

    if st.session_state.api_key_saved and st.session_state.api_key:
        masked = st.session_state.api_key[:10] + "..." + st.session_state.api_key[-4:]
        st.markdown(f'<div class="key-status-ok">✅ 当前 Key: <code>{masked}</code> · 已就绪</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="key-status-missing">⚠️ 尚未配置 API Key，请先输入 Key 后再使用分析功能</div>', unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════
#  功能切换 Tab
# ══════════════════════════════════════════════════════════
tab_dsa, tab_trading = st.tabs(["📊 每日股票分析 (DSA)", "🤖 多智能体交易分析 (TradingAgents)"])

# ══════════════════════════════════════════════════════════
#  Tab 1: 每日股票分析 (DSA) - iframe 嵌入
# ══════════════════════════════════════════════════════════
with tab_dsa:
    st.markdown("### 📊 每日股票分析")
    st.markdown("AI 驱动的每日股票深度分析系统，支持自动定时分析、技术面/基本面/消息面综合研判。")

    dsa_col1, dsa_col2 = st.columns([3, 1])
    with dsa_col1:
        st.markdown(f"**服务地址:** [`{DSA_URL}`]({DSA_URL})")
    with dsa_col2:
        if st.button("🔗 新窗口打开 DSA", use_container_width=True):
            st.markdown(f'<script>window.open("{DSA_URL}", "_blank")</script>', unsafe_allow_html=True)

    # 同步 API Key 到 DSA 服务
    if st.session_state.api_key_saved and st.session_state.api_key:
        with st.expander("⚙️ 同步 API Key 到 DSA 服务", expanded=False):
            st.markdown("点击下方按钮将当前 API Key 同步到每日股票分析服务的配置中。")
            if st.button("🔄 同步 Key 到 DSA"):
                try:
                    # 先获取当前配置版本
                    config_resp = requests.get(f"{DSA_URL}/api/v1/system/config", params={"include_schema": True}, timeout=10)
                    if config_resp.status_code == 200:
                        config_data = config_resp.json()
                        config_version = config_data.get("config_version", "")

                        # 更新 OpenRouter 渠道的 API Key
                        update_items = [
                            {"key": "LLM_CHANNELS", "value": "openrouter"},
                            {"key": "LLM_OPENROUTER_PROTOCOL", "value": "openai"},
                            {"key": "LLM_OPENROUTER_BASE_URL", "value": "https://openrouter.ai/api/v1"},
                            {"key": "LLM_OPENROUTER_API_KEY", "value": st.session_state.api_key},
                            {"key": "LLM_OPENROUTER_MODELS", "value": "anthropic/claude-opus-4.6,anthropic/claude-sonnet-4-5,openai/gpt-4o,openai/gpt-4o-mini,google/gemini-2.5-pro-preview-03-25,deepseek/deepseek-chat-v3-0324"},
                            {"key": "LLM_OPENROUTER_ENABLED", "value": "true"},
                        ]

                        update_resp = requests.put(
                            f"{DSA_URL}/api/v1/system/config",
                            json={
                                "config_version": config_version,
                                "mask_token": "******",
                                "reload_now": True,
                                "items": update_items,
                            },
                            timeout=15,
                        )
                        if update_resp.status_code == 200:
                            st.success("✅ API Key 已成功同步到 DSA 服务！")
                        else:
                            st.warning(f"同步返回状态码 {update_resp.status_code}，可能需要手动配置。")
                    else:
                        st.error(f"无法连接 DSA 服务（状态码 {config_resp.status_code}）")
                except requests.exceptions.RequestException as e:
                    st.error(f"连接 DSA 服务失败: {e}")

    # iframe 嵌入
    st.markdown(
        f'<div class="dsa-iframe-container">'
        f'<iframe src="{DSA_URL}" width="100%" height="800" frameborder="0" '
        f'style="border-radius:12px;" allow="clipboard-write"></iframe>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════
#  Tab 2: 多智能体交易分析 (TradingAgents)
# ══════════════════════════════════════════════════════════
with tab_trading:
    st.markdown("### 🤖 多智能体交易分析")
    st.markdown("基于 TradingAgents 框架的多 Agent 协同分析：基本面、技术面、情绪分析 + 多空辩论 + 风险评估。")

    # ── 配置区域 ──────────────────────────────────────────
    with st.container():
        row1_col1, row1_col2, row1_col3 = st.columns([2, 2, 3])

        with row1_col1:
            raw_ticker = st.text_input(
                "🏷️ 股票代码",
                value="AAPL",
                placeholder="AAPL / 00700 / 600519",
                help="美股直接输入代码，港股输入数字（如 00700），A股输入6位代码（如 600519）",
                key="ta_ticker",
            ).strip()
            ticker = normalize_stock_code(raw_ticker)
            if ticker != raw_ticker.strip().upper():
                st.markdown(f'<div class="stock-hint">自动转换为: <b>{ticker}</b></div>', unsafe_allow_html=True)

        with row1_col2:
            analysis_date = st.date_input(
                "📅 分析日期",
                value=datetime.date.today() - datetime.timedelta(days=1),
                max_value=datetime.date.today() - datetime.timedelta(days=1),
                help="选择要分析的交易日期",
                key="ta_date",
            )

        with row1_col3:
            provider_keys = list(PROVIDER_MODELS.keys())
            provider_labels = [PROVIDER_MODELS[k]["label"] for k in provider_keys]
            selected_label = st.selectbox(
                "🤖 LLM 提供商",
                options=provider_labels,
                index=0,
                key="ta_provider",
            )
            llm_provider = provider_keys[provider_labels.index(selected_label)]

        models = PROVIDER_MODELS[llm_provider]["models"]

        row2_col1, row2_col2, row2_col3, row2_col4 = st.columns([3, 3, 1.5, 1.5])

        with row2_col1:
            deep_think_model = st.selectbox(
                "🧠 深度思考模型（主分析）",
                options=models,
                index=0,
                help="用于深度分析的主力模型，消耗 Token 较多",
                key="ta_deep",
            )

        with row2_col2:
            quick_think_model = st.selectbox(
                "⚡ 快速思考模型（辅助）",
                options=models,
                index=min(1, len(models) - 1),
                help="用于快速判断的辅助模型，消耗 Token 较少",
                key="ta_quick",
            )

        with row2_col3:
            max_debate_rounds = st.number_input(
                "⚔️ 辩论轮数",
                min_value=1, max_value=3, value=1,
                help="多空辩论轮数，越多越深入",
                key="ta_debate",
            )

        with row2_col4:
            max_risk_rounds = st.number_input(
                "🛡️ 风险轮数",
                min_value=1, max_value=3, value=1,
                help="风险讨论轮数",
                key="ta_risk",
            )

        # API Key 状态 + 开始按钮
        row3_col1, row3_col2 = st.columns([4, 1])

        with row3_col1:
            if st.session_state.api_key_saved and st.session_state.api_key:
                masked = st.session_state.api_key[:10] + "..." + st.session_state.api_key[-4:]
                st.markdown(f'<div class="key-status-ok">🔑 使用顶部配置的 Key: <code>{masked}</code></div>', unsafe_allow_html=True)
                api_key_override = st.text_input(
                    "覆盖 Key（可选）",
                    type="password",
                    placeholder="留空则使用顶部配置的 Key",
                    key="ta_key_override",
                    label_visibility="collapsed",
                )
            else:
                api_key_override = st.text_input(
                    "🔑 API Key",
                    type="password",
                    placeholder="请先在顶部配置 API Key，或在此输入",
                    key="ta_key_direct",
                )

        with row3_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True, key="ta_analyze")

    st.markdown("---")

    # ── 功能介绍（未分析时显示） ──────────────────────────
    if not analyze_btn and "analysis_result" not in st.session_state:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info("🔍 **基本面分析**\n\n财务报表、估值指标、行业对比")
        with col2:
            st.info("📊 **技术面分析**\n\n均线、RSI、MACD、成交量")
        with col3:
            st.info("📰 **情绪分析**\n\n新闻资讯、市场情绪、社交媒体")
        with col4:
            st.info("⚖️ **多空辩论**\n\n多方/空方 Agent 辩论，风险评估")

        st.markdown("---")
        st.markdown("### 📖 支持的股票代码格式")
        st.markdown("""
| 市场 | 输入格式 | 示例 | 自动转换 |
|------|---------|------|---------|
| 🇺🇸 美股 | 直接输入代码 | `AAPL`、`NVDA`、`TSLA` | 无需转换 |
| 🇭🇰 港股 | 输入数字代码 | `00700`、`09988`、`03690` | → `0700.HK` |
| 🇨🇳 A股（上证） | 输入6位代码 | `600519`、`601318` | → `600519.SS` |
| 🇨🇳 A股（深证） | 输入6位代码 | `000001`、`300750` | → `000001.SZ` |
""")

    # ── 执行分析 ──────────────────────────────────────────
    if analyze_btn:
        if not ticker:
            st.error("请输入股票代码！")
            st.stop()

        # 确定最终 API Key
        final_api_key = api_key_override if ('api_key_override' in dir() and api_key_override) else st.session_state.api_key
        if not final_api_key:
            st.error("请先在顶部配置 API Key！")
            st.stop()

        # 设置环境变量
        if llm_provider == "openrouter":
            os.environ["OPENROUTER_API_KEY"] = final_api_key
            os.environ["OPENAI_API_KEY"] = final_api_key
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        elif llm_provider == "openai":
            os.environ["OPENAI_API_KEY"] = final_api_key
        elif llm_provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = final_api_key
        elif llm_provider == "google":
            os.environ["GOOGLE_API_KEY"] = final_api_key

        st.markdown(f"## 📋 {ticker} · {analysis_date} 分析报告")
        st.markdown("---")

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

            if llm_provider == "openrouter":
                config["backend_url"] = "https://openrouter.ai/api/v1"
                config["llm_provider"] = "openai"
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
            _, decision, final_state = ta.propagate(ticker, trade_date_str)

            update_progress(5, 7, "多空辩论与风险评估中...")
            update_progress(6, 7, "生成最终交易决策...")
            update_progress(7, 7, "分析完成！")

            progress_placeholder.empty()
            status_placeholder.empty()
            log_placeholder.empty()

            st.session_state["analysis_result"] = {
                "ticker": ticker,
                "date": trade_date_str,
                "decision": decision,
                "state": final_state,
                "deep_model": deep_think_model,
                "quick_model": quick_think_model,
                "debate_rounds": max_debate_rounds,
            }

            # ── 展示结果 ──────────────────────────────────
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
    "AI 股票分析平台 · "
    "<a href='https://github.com/xmkinc/daily_stock_analysis' target='_blank'>每日分析</a> · "
    "<a href='https://github.com/xmkinc/TradingAgents' target='_blank'>TradingAgents</a> · "
    "Powered by OpenRouter + LLM"
    "</div>",
    unsafe_allow_html=True,
)
