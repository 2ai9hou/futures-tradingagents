from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_main_contract(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb' for rebar, 'hc' for hot rolled coil"],
    exchange: Annotated[str, "exchange code: 'dce', 'czce', 'shfe', 'cffex'"] = None,
) -> str:
    """
    Retrieve the main contract code for a given futures symbol.
    Uses akshare data source.
    
    Args:
        symbol: Futures symbol code (e.g., 'rb' for rebar, 'hc' for hot rolled coil, 'i' for iron ore)
        exchange: Exchange code (optional)
    
    Returns:
        str: Main contract code (e.g., 'rb0', 'rb2410')
    """
    return route_to_vendor("get_main_contract", symbol, exchange)


@tool
def get_futures_ohlc(
    symbol: Annotated[str, "main contract code, e.g. 'rb2410' or 'rb0'"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve daily K-line data (OHLCV + open interest) for a futures contract.
    Uses akshare data source.
    
    Args:
        symbol: Main contract code (e.g., 'rb2410')
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    
    Returns:
        str: Formatted dataframe containing daily bar data
    """
    return route_to_vendor("get_futures_ohlc", symbol, start_date, end_date)
