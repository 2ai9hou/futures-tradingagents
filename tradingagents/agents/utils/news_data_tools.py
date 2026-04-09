from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_futures_news(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb'"],
) -> str:
    """
    Retrieve news data for a given futures symbol.
    Uses akshare data source.
    
    Args:
        symbol: Futures symbol code
    
    Returns:
        str: A formatted string containing news data
    """
    return route_to_vendor("get_futures_news", symbol)


@tool
def get_global_futures_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
) -> str:
    """
    Retrieve global futures market news and macroeconomic indicators.
    Uses akshare data source.
    
    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back (default 7)
    
    Returns:
        str: A formatted string containing global futures news
    """
    return route_to_vendor("get_futures_news")
