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
            """You are a futures market analyst tasked with analyzing Chinese futures markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy. Categories and each category's indicators are:

Moving Averages:
- sma: Simple Moving Average, for identifying trend direction and dynamic support/resistance levels
- ema: Exponential Moving Average, more responsive to recent price changes

Momentum Indicators:
- macd: Moving Average Convergence Divergence, for identifying trend changes and momentum

Volatility Indicators:
- boll: Bollinger Bands, for spotting breakouts or reversals based on price volatility

Volume-Based Indicators:
- volume: Trading volume, to confirm trends by integrating price action with volume data
- position: Open interest, to assess market participation and sentiment

- First, use get_main_contract to get the main contract code for the futures symbol.
- Then, use get_futures_ohlc to retrieve daily K-line data (OHLCV + open interest).
- Finally, use get_futures_indicators with the specific indicator names to get technical analysis.
- Write a very detailed and nuanced report of the trends you observe.
- Provide specific, actionable insights with supporting evidence to help traders make informed decisions.
- Append a Markdown table at the end of the report to organize key points."""
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
