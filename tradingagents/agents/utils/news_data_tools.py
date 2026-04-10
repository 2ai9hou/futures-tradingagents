from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_market_news(
    look_back_hours: Annotated[int, "回溯小时数，默认24小时"] = 24,
) -> str:
    """
    获取市场7x24小时实时快讯。
    数据来源：华尔街见闻/东方财富。

    Args:
        look_back_hours: 回溯小时数 (默认24小时)

    Returns:
        str: 格式化的时间线式新闻文本，包含标题、时间、来源
    """
    return route_to_vendor("get_market_news", look_back_hours)


@tool
def get_futures_news(
    symbol: Annotated[str, "期货品种代码，如 'rb'、'IF'、'm'"],
) -> str:
    """
    获取新浪财经指定期货品种的相关快讯。

    Args:
        symbol: 期货品种代码 (如 'rb' 螺纹钢, 'IF' 沪深300)

    Returns:
        str: 格式化品种相关新闻文本
    """
    return route_to_vendor("get_sina_futures_news", symbol)


@tool
def get_futures_research_reports(
    symbol: Annotated[str, "期货品种代码，如 'rb'、'IF'"],
    limit: Annotated[int, "返回研报数量，默认10篇"] = 10,
) -> str:
    """
    获取东方财富期货品种最新研报摘要。

    Args:
        symbol: 期货品种代码 (如 'rb' 螺纹钢, 'IF' 沪深300)
        limit: 返回研报数量 (默认10篇)

    Returns:
        str: 格式化研报摘要文本，包含标题、分析师、评级、核心观点
    """
    return route_to_vendor("get_futures_research_reports", symbol, limit)


@tool
def get_macro_news(
    look_back_days: Annotated[int, "回溯天数，默认7天"] = 7,
) -> str:
    """
    获取宏观新闻和经济数据预告。
    数据来源：东方财富宏观数据。

    Args:
        look_back_days: 回溯天数 (默认7天)

    Returns:
        str: 格式化宏观新闻文本
    """
    return route_to_vendor("get_macro_news", look_back_days)
