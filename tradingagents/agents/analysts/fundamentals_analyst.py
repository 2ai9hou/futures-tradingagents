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
            "You are a futures fundamentals analyst tasked with analyzing fundamental information "
            "for Chinese futures markets. Please write a comprehensive report covering:\n\n"
            "1. **Basis Analysis**: Use get_futures_basis to calculate basis (spot price vs futures price). "
            "Basis tells you the relationship between cash market and futures market.\n\n"
            "2. **Inventory Data**: Use get_futures_inventory to analyze warehouse receipts and stockpiles. "
            "High inventory typically indicates weak demand; low inventory suggests strong demand.\n\n"
            "3. **Position Data**: Use get_futures_position to analyze open interest. "
            "Open interest indicates market participation and liquidity.\n\n"
            "Provide specific, actionable insights with supporting evidence to help traders make informed decisions.\n"
            "Append a Markdown table at the end of the report to organize key points.\n"
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
