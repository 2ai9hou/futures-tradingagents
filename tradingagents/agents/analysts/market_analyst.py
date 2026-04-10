from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_futures_indicators,
    get_language_instruction,
    get_main_contract,
    get_futures_ohlc,
)


def create_market_analyst(llm):
    def market_analyst_node(state):
        current_date = state["trade_date"]
        company = state["company_of_interest"]
        position = state.get("position_direction", "Long")
        instrument_context = build_instrument_context(company, position=position)

        tools = [
            get_main_contract,
            get_futures_ohlc,
            get_futures_indicators,
        ]

        system_message = (
            """你是一位期货技术分析师，专注于中国期货市场的技术面分析。

【核心职责】
你必须通过分析价格走势、成交量和持仓量的配合关系，来判断市场多空力量对比和趋势可持续性。

【分析框架】

1. **价格与持仓量配合分析（最重要）**
   - 增仓上行：价格上涨 + 持仓量增加 → 多头主动推涨，趋势可能延续
   - 增仓下行：价格下跌 + 持仓量增加 → 空头主动打压，趋势可能延续
   - 减仓上行：价格上涨 + 持仓量减少 → 多头获利平仓，上涨动力不足，警惕反转
   - 减仓下行：价格下跌 + 持仓量减少 → 空头获利平仓，下跌动力不足，警惕反弹
   - 平仓僵局：价格震荡 + 持仓量大幅下降 → 多空双方观望，等待突破方向

2. **成交量与价格配合分析**
   - 放量突破：成交量放大 + 价格突破关键位 → 突破有效性高
   - 缩量整理：成交量萎缩 + 价格震荡 → 蓄势待发
   - 天量见天价：异常巨量 + 价格创新高 → 警惕顶部

3. **技术指标分析**
   - MACD：判断趋势方向与动能强弱
   - RSI：判断超买超卖
   - 布林带：判断价格通道与波动率
   - 均线系统：判断支撑压力

4. **持仓量结构分析**
   - 关注主力和约持仓变化
   - 分析多空主力持仓动向
   - 判断是否存在逼仓风险

【分析步骤】
1. 使用 get_main_contract 获取主力合约代码
2. 使用 get_futures_ohlc 获取K线数据（含成交量、持仓量）
3. 使用 get_futures_indicators 获取MACD、RSI、布林带等技术指标
4. 综合分析价格、成交量、持仓量的配合关系

【输出要求】
1. 详细分析持仓量变化与价格走势的配合关系
2. 判断当前趋势的多空力量对比
3. 给出技术面综合评级（强烈看多/看多/中性/看空/强烈看空）
4. 识别关键支撑位和压力位
5. 提示可能的风险点（如减仓背离等）

请用中文撰写完整的技术分析报告，并以Markdown表格总结关键数据。"""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
