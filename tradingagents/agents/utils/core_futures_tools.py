from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_main_contract(
    symbol: Annotated[str, "期货品种代码，如 'rb'（螺纹钢）、'hc'（热轧卷板）、'i'（铁矿石）"],
    exchange: Annotated[str, "交易所代码: 'dce'（大连）、'czce'（郑商）、'shfe'（上海）、'cffex'（中金）"] = None,
) -> str:
    """
    获取期货主力合约代码。
    使用 akshare 数据源。

    Args:
        symbol: 期货品种代码 (如 'rb' 螺纹钢, 'hc' 热轧卷板, 'i' 铁矿石)
        exchange: 交易所代码 (可选)

    Returns:
        str: 主力合约代码 (如 'rb0', 'rb2410')
    """
    return route_to_vendor("get_main_contract", symbol, exchange)


@tool
def get_futures_ohlc(
    symbol: Annotated[str, "主力合约代码，如 'rb2410' 或 'rb0'"],
    start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
    end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
) -> str:
    """
    获取期货合约日线K线数据（OHLCV + 持仓量）。
    使用 akshare 数据源。

    Args:
        symbol: 主力合约代码 (如 'rb2410')
        start_date: 开始日期 (格式: yyyy-mm-dd)
        end_date: 结束日期 (格式: yyyy-mm-dd)

    Returns:
        str: 格式化的时间序列数据
    """
    return route_to_vendor("get_futures_ohlc", symbol, start_date, end_date)
