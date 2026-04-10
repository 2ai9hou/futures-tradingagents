from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_futures_news,
    get_global_futures_news,
)


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        company = state["company_of_interest"]
        position = state.get("position_direction", "Long")
        instrument_context = build_instrument_context(company, position=position)

        tools = [
            get_futures_news,
            get_global_futures_news,
        ]

        system_message = (
            """你是一位期货宏观与政策分析师，专注于中国期货市场的消息面分析和政策影响评估。

【核心职责】
你必须追踪可能影响期货市场的宏观政策、行业动态和突发事件，帮助判断短期价格波动和趋势转折点。

【分析框架】

1. **中国央行政策**
   - LPR（贷款市场报价利率）：影响企业融资成本，间接影响商品需求
   - MLF（中期借贷便利）：观察央行投放力度，判断流动性宽松程度
   - 存款准备金率：政策宽松/收紧信号
   - 货币政策取向：松紧直接影响市场情绪和资金成本

2. **发改委政策动向**
   - 产业政策：淘汰落后产能、环保限产等
   - 价格调控：某些品种存在政策价格上限或下限
   - 储备投放：收储/放储消息对价格的短期冲击
   - 行业规划：重大产业规划影响长期供需格局

3. **美联储与海外宏观**
   - 非农数据：影响美元走势，间接影响大宗商品
   - CPI/PPI：通胀预期影响商品配置需求
   - 加息/降息预期：全球流动性周期
   - 地缘政治：突发事件影响商品供应链

4. **产业链突发新闻**
   - 钢厂检修计划：影响原材料需求预期
   - 天气炒作：雨季、台风、高温等影响农产品/能源
   - 事故灾害：矿难、火灾等影响供应
   - 贸易政策：进出口政策变化
   - 谣言与传闻：市场情绪放大器

【分析步骤】
1. 使用 get_futures_news 获取品种相关行业新闻
2. 使用 get_global_futures_news 获取宏观和市场情绪新闻
3. 评估各类消息对供需和价格的可能影响

【输出要求】
1. 梳理近期重大宏观政策变化
2. 分析各类消息对市场的短期影响
3. 判断消息面的多空倾向（利多/利空/中性）
4. 评估消息冲击的持续性（一日游/趋势性）
5. 提示需要持续关注的后续事件

请用中文撰写完整的消息面分析报告，并以Markdown表格分类汇总各类信息。"""
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
            "news_report": report,
        }

    return news_analyst_node
