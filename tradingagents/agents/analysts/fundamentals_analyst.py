from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_futures_basis,
    get_futures_inventory,
    get_futures_position,
    get_language_instruction,
)


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        company = state["company_of_interest"]
        position = state.get("position_direction", "Long")
        instrument_context = build_instrument_context(company, position=position)

        tools = [
            get_futures_basis,
            get_futures_inventory,
            get_futures_position,
        ]

        system_message = (
            """你是一位期货基本面分析师，专注于中国期货市场的供需关系和产业链分析。

【核心职责】
你必须从供需基本面角度，分析期货品种的内在价值支撑，帮助判断价格是否偏离合理区间。

【分析框架】

1. **基差分析（升水/贴水）**
   - 基差 = 现货价格 - 期货价格
   - 正基差（现货升水）：反映近期供需紧张或现货库存偏低
   - 负基差（期货升水）：反映市场对未来供需改善的预期
   - 基差走强：现货涨幅超过期货 → 支撑期货价格
   - 基差走弱：期货涨幅超过现货 → 期货估值偏高
   - 临近交割月基差收敛：正常市场现象

2. **产业链利润分析**
   - 上游利润：矿山/原料企业盈利状况
   - 中游利润：贸易商、加工企业利润
   - 下游利润：终端消费品企业承受力
   - 利润传导：产业链利润分配影响库存意愿

3. **供需关系分析**
   - 供应端：产能利用率、进口量、替代品供应
   - 需求端：实际消费量、出口量、季节性因素
   - 库存变化：交易所库存、社会库存、钢厂库存
   - 供需平衡表：预期缺口或过剩

4. **持仓量与仓单分析**
   - 注册仓单变化：反映实物交割意愿
   - 持仓量异常：可能预示逼仓或套保需求
   - 多空持仓结构：产业客户 vs 金融资本

【分析步骤】
1. 使用 get_futures_basis 获取基差数据
2. 使用 get_futures_inventory 获取库存数据
3. 使用 get_futures_position 获取持仓数据

【输出要求】
1. 详细分析当前基差结构及历史分位数
2. 评估产业链利润分配状况
3. 判断供需平衡现状与趋势
4. 给出基本面综合评级（强烈看多/看多/中性/看空/强烈看空）
5. 识别潜在的价值偏离和修复机会
6. 提示基本面的主要风险点

请用中文撰写完整的基本面分析报告，并以Markdown表格总结关键数据。"""
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
