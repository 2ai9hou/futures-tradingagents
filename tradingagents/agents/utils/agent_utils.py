from langchain_core.messages import HumanMessage, RemoveMessage
from typing import Optional, Literal

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.agents.utils.news_data_tools import (
    get_futures_news,
    get_global_futures_news,
)

PositionDirection = Literal["Long", "Short"]

CHINESE_FUTURES_EXCHANGES = {"SHFE", "DCE", "CZCE", "CFFEX"}

CHINESE_FUTURES_SPECIES_CN = {
    "rb": "螺纹钢", "hc": "热轧卷板", "i": "铁矿石", "j": "焦炭",
    "m": "豆粕", "y": "豆油", "p": "棕榈油", "a": "大豆", "b": "铁矿石",
    "c": "玉米", "cs": "玉米淀粉", "l": "聚乙烯", "v": "聚氯乙烯",
    "pp": "聚丙烯", "eg": "乙二醇", "eb": "苯乙烯", "jd": "鸡蛋",
    "lh": "生猪", "sf": "硅铁", "sm": "锰硅",
    "IF": "沪深300股指", "IH": "上证50股指", "IC": "中证500股指",
    "IM": "中证1000股指", "T": "10年期国债", "TF": "5年期国债", "TS": "2年期国债",
    "au": "黄金", "ag": "白银", "cu": "铜", "al": "铝", "zn": "锌",
    "pb": "铅", "ni": "镍", "sn": "锡", "ss": "不锈钢",
    "ru": "天然橡胶", "bu": "沥青", "sc": "原油", "nr": "20号胶",
}


def get_main_contract(
    symbol: str,
    exchange: str = None,
) -> str:
    """
    Get the main contract code for a given futures symbol.
    
    Args:
        symbol: Futures symbol code (e.g., 'rb' for rebar, 'hc' for hot rolled coil)
        exchange: Exchange code (optional)
    
    Returns:
        Main contract code string
    """
    if exchange:
        return route_to_vendor("get_main_contract", symbol, exchange)
    return route_to_vendor("get_main_contract", symbol)


def get_futures_ohlc(
    symbol: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Get OHLC daily bars for a futures contract.
    
    Args:
        symbol: Main contract code (e.g., 'rb2410')
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    
    Returns:
        Formatted OHLC data string
    """
    return route_to_vendor("get_futures_ohlc", symbol, start_date, end_date)


def get_futures_indicators(
    symbol: str,
    indicator: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Get technical indicators for a futures contract.
    
    Args:
        symbol: Main contract code
        indicator: Indicator type (volume, position, sma, ema, macd, boll)
        start_date: Start date
        end_date: End date
    
    Returns:
        Formatted indicator data string
    """
    return route_to_vendor("get_futures_indicators", symbol, indicator, start_date, end_date)


def get_futures_basis(
    symbol: str,
    spot_price: float,
    date: str = None,
) -> str:
    """
    Get basis data (spot vs futures) for a futures symbol.
    
    Args:
        symbol: Futures symbol code
        spot_price: Current spot price
        date: Trading date (optional)
    
    Returns:
        Formatted basis data string
    """
    return route_to_vendor("get_futures_basis", symbol, spot_price, date)


def get_futures_inventory(
    symbol: str,
    date: str = None,
) -> str:
    """
    Get inventory data for a futures symbol.
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional)
    
    Returns:
        Formatted inventory data string
    """
    return route_to_vendor("get_futures_inventory", symbol, date)


def get_futures_position(
    symbol: str,
    date: str = None,
) -> str:
    """
    Get position data (open interest) for a futures symbol.
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional)
    
    Returns:
        Formatted position data string
    """
    return route_to_vendor("get_futures_position", symbol, date)


def get_futures_news() -> str:
    """Get futures market news (placeholder)."""
    return route_to_vendor("get_futures_news")


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def build_instrument_context(
    species: str,
    exchange: Optional[str] = None,
    position: PositionDirection = "Long",
) -> str:
    """Describe the exact instrument so agents preserve proper futures tickers.

    Args:
        species: Futures species code (e.g., 'rb', 'IF', 'm')
        exchange: Exchange code (SHFE, DCE, CZCE, CFFEX)
        position: Position direction (Long or Short)

    Returns:
        str: Context string for the agent
    """
    species_upper = species.upper()
    exchange_upper = exchange.upper() if exchange else None
    cn_name = CHINESE_FUTURES_SPECIES_CN.get(species_upper, species_upper)
    if cn_name == species_upper:
        cn_name = CHINESE_FUTURES_SPECIES_CN.get(species_upper.lower(), species_upper)

    if exchange_upper:
        ticker_display = f"{exchange_upper}:{species_upper}"
    else:
        ticker_display = species_upper

    context_parts = [
        f"The instrument to analyze is `{ticker_display}` ({cn_name}).",
        f"Position direction: {position}.",
        f"Use this exact ticker in every tool call, report, and recommendation.",
    ]

    if exchange_upper:
        context_parts.append(
            f"Exchange: {exchange_upper}. "
            f"Available exchanges: SHFE (Shanghai), DCE (Dalian), CZCE (Zhengzhou), CFFEX (CFFEX)."
        )

    context_parts.append(
        f"For Chinese futures: use main contract codes like 'rb0', 'hc0', 'i0'."
    )

    if position == "Long":
        context_parts.append(
            "This is a LONG position - you expect the price to rise."
        )
    else:
        context_parts.append(
            "This is a SHORT position - you expect the price to fall."
        )

    return " ".join(context_parts)


def build_instrument_context_from_ticker(ticker: str) -> str:
    """Build instrument context from a formatted ticker string.

    Supports formats:
    - 'rb' -> species only
    - 'SHFE:rb' -> with exchange
    - 'rb|Long' -> with position
    - 'SHFE:rb|Short' -> full format
    """
    import re

    position: PositionDirection = "Long"
    exchange: Optional[str] = None
    species = ticker

    if match := re.match(r"^(SHFE|DCE|CZCE|CFFEX):([A-Z0-9]+)(?:\|(LONG|SHORT))?$", ticker.upper()):
        exchange, species, pos = match.groups()
        if pos:
            position = "Long" if pos == "LONG" else "Short"
    elif match := re.match(r"^([A-Z0-9]+)\|(LONG|SHORT)$", ticker.upper()):
        species, pos = match.groups()
        position = "Long" if pos == "LONG" else "Short"

    return build_instrument_context(species, exchange, position)


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages
