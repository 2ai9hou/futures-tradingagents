from typing import Annotated

from .akshare_futures import (
    get_main_contract_code,
    get_futures_daily_bars,
    get_futures_ohlc,
    get_futures_basis,
    get_futures_inventory,
    get_futures_position,
    get_futures_historical_indicators,
)

from .config import get_config

TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "Futures daily K-line data (OHLCV)",
        "tools": [
            "get_main_contract",
            "get_futures_ohlc",
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators for futures",
        "tools": [
            "get_futures_indicators",
        ]
    },
    "fundamental_data": {
        "description": "Futures fundamentals (basis, inventory, position)",
        "tools": [
            "get_futures_basis",
            "get_futures_inventory",
            "get_futures_position",
        ]
    },
    "news_data": {
        "description": "Futures market news (placeholder)",
        "tools": [
            "get_futures_news",
        ]
    }
}

VENDOR_LIST = [
    "akshare",
]


VENDOR_METHODS = {
    "get_main_contract": {
        "akshare": get_main_contract_code,
    },
    "get_futures_ohlc": {
        "akshare": get_futures_daily_bars,
    },
    "get_futures_indicators": {
        "akshare": get_futures_historical_indicators,
    },
    "get_futures_basis": {
        "akshare": get_futures_basis,
    },
    "get_futures_inventory": {
        "akshare": get_futures_inventory,
    },
    "get_futures_position": {
        "akshare": get_futures_position,
    },
    "get_futures_news": {
        "akshare": lambda: "News functionality not yet implemented for akshare futures.",
    },
}


def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")


def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    return config.get("data_vendors", {}).get(category, "akshare")


def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation."""
    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    vendor = get_vendor(get_category_for_method(method), method)
    
    if vendor not in VENDOR_METHODS[method]:
        vendor = list(VENDOR_METHODS[method].keys())[0]

    impl = VENDOR_METHODS[method][vendor]
    return impl(*args, **kwargs)
