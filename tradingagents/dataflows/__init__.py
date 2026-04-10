"""
TradingAgents Dataflows Module

Data fetching and processing for Chinese futures market.
"""

from .akshare_futures import (
    get_main_contract_code,
    get_futures_daily_bars,
    get_futures_ohlc,
    get_futures_basis,
    get_futures_inventory,
    get_futures_position,
    get_futures_historical_indicators,
    get_market_news,
    get_sina_futures_news,
    get_futures_research_reports,
    get_macro_news,
)

from .trading_time import (
    TradingSession,
    TradingSessionType,
    TRADING_SESSIONS,
    CONTRACT_EXCHANGES,
    get_trading_session,
    is_night_session_contract,
    normalize_night_session_datetime,
    normalize_night_session_df,
    filter_trading_hours,
    get_continuous_trading_dates,
    get_session_info,
    is_valid_trading_time,
    create_trading_calendar,
)

from .main_contract import (
    ContractRollover,
    ContinuousDataResult,
    MainContractTracker,
    ContinuousFuturesEngine,
    get_rollover_indicator_status,
)

__all__ = [
    # akshare futures
    "get_main_contract_code",
    "get_futures_daily_bars",
    "get_futures_ohlc",
    "get_futures_basis",
    "get_futures_inventory",
    "get_futures_position",
    "get_futures_historical_indicators",
    "get_market_news",
    "get_sina_futures_news",
    "get_futures_research_reports",
    "get_macro_news",
    # trading time
    "TradingSession",
    "TradingSessionType",
    "TRADING_SESSIONS",
    "CONTRACT_EXCHANGES",
    "get_trading_session",
    "is_night_session_contract",
    "normalize_night_session_datetime",
    "normalize_night_session_df",
    "filter_trading_hours",
    "get_continuous_trading_dates",
    "get_session_info",
    "is_valid_trading_time",
    "create_trading_calendar",
    # main contract
    "ContractRollover",
    "ContinuousDataResult",
    "MainContractTracker",
    "ContinuousFuturesEngine",
    "get_rollover_indicator_status",
]
