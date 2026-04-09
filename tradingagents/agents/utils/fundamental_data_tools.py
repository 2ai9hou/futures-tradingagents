from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_futures_basis(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb'"],
    spot_price: Annotated[float, "current spot price of the underlying asset"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve basis data (spot price vs futures price) for a given futures symbol.
    Uses akshare data source.
    
    Args:
        symbol: Futures symbol code (e.g., 'rb' for rebar)
        spot_price: Current spot price of the underlying asset
        date: Trading date (optional, defaults to today)
    
    Returns:
        str: Formatted report containing basis data
    """
    return route_to_vendor("get_futures_basis", symbol, spot_price, date)


@tool
def get_futures_inventory(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb' for rebar, 'hc' for hot rolled coil"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve inventory data (warehouse receipts, stockpiles) for a given futures symbol.
    Uses akshare data source.
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional)
    
    Returns:
        str: Formatted report containing inventory data
    """
    return route_to_vendor("get_futures_inventory", symbol, date)


@tool
def get_futures_position(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb'"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve open interest and position data for a given futures symbol.
    Uses akshare data source.
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional)
    
    Returns:
        str: Formatted report containing position data
    """
    return route_to_vendor("get_futures_position", symbol, date)
