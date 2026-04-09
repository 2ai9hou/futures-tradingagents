from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_futures_indicators(
    symbol: Annotated[str, "main contract code, e.g. 'rb2410'"],
    indicator: Annotated[str, "technical indicator type: 'volume', 'position', 'sma', 'ema', 'macd', 'boll'"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "number of days to look back (used if start_date not provided)"] = 30,
) -> str:
    """
    Retrieve technical indicators for a given futures contract.
    Uses akshare data source.
    
    Args:
        symbol: Main contract code (e.g., 'rb2410')
        indicator: Technical indicator type: volume, position, sma, ema, macd, boll
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
        look_back_days: Number of days to look back (default 30)
    
    Returns:
        str: Formatted dataframe containing technical indicators
    """
    return route_to_vendor("get_futures_indicators", symbol, indicator, start_date, end_date)
