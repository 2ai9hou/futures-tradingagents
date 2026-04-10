from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.news_data_tools import (
    get_market_news,
    get_futures_news,
    get_futures_research_reports,
)


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        company = state["company_of_interest"]
        position = state.get("position_direction", "Long")
        instrument_context = build_instrument_context(company, position=position)

        tools = [
            get_market_news,
            get_futures_news,
            get_futures_research_reports,
        ]

        system_message = (
            """你是一位期货市场情绪分析师，专注于捕捉市场参与者的情绪变化和预期差异。

【核心职责】
你必须通过分析市场交投情绪、机构观点分歧和投资者行为偏差，来判断市场是否过度乐观或悲观。

【分析框架】

1. **多空情绪指标**
   - 市场整体持仓变化：反映多空双方参与度
   - 合约价差变化：近远月价差反映市场预期
   - 成交量变化：量能放大/萎缩反映市场活跃度
   - 虚实盘比：持仓量 vs 现货量的比值

2. **机构观点分析**
   - 主流机构评级变化：多空转向信号
   - 期货公司研报倾向：综合判断市场共识
   - 持仓报告解读：多空主力持仓动向
   - 明星席位动向：主力席位增减仓

3. **产业链情绪**
   - 贸易商心态：挺价意愿 vs 抛售压力
   - 钢厂采购策略：逢低补库 vs 随用随采
   - 终端需求预期：旺季/淡季情绪转换
   - 替代品动态：相关品种联动情绪

4. **行为金融视角**
   - 恐慌指数：市场波动率指数
   - 期现价差异常：情绪过热/过冷信号
   - 合约单边持仓集中度：逼仓风险
   - 散户 vs 机构情绪差：逆向指标参考

5. **研报情绪分析**
   - 评级分布：买入/中性/卖出比例
   - 目标价空间：上涨/下跌空间
   - 分析师信心指数：预期分歧度

【分析步骤】
1. 使用 get_market_news 获取7x24快讯，捕捉市场情绪变化
2. 使用 get_futures_news 获取品种相关新闻和评论
3. 使用 get_futures_research_reports 获取机构评级和目标价

【输出要求】
1. 评估当前市场整体情绪（极度看多/偏多/中性/偏空/极度看空）
2. 识别多空双方的主要分歧点
3. 判断情绪是否出现极端偏离
4. 提示可能的市场情绪拐点信号
5. 给出情绪面综合评级

请用中文撰写完整的情绪分析报告，并以Markdown表格总结各类情绪指标。"""
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
