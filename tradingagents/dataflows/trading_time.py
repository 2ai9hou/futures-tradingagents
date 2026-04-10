"""
Trading Time Normalization Module

中国期货交易时间处理：
1. 定义各品种交易时段（日盘/夜盘）
2. 将夜盘数据归入次日交易日
3. 过滤非交易时段数据
4. 确保时间轴连续性

夜盘归入次日规则：
- 交易日的判定：亚洲时段以9:00为分界
- 21:00-23:59 的夜盘数据 → 归属次日
- 00:00-02:30 的夜盘数据 → 归属次日
- 例如：2024-01-15 21:00 的沪铜交易 → 记为 2024-01-16
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, TypedDict
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class TradingSessionType(Enum):
    """交易时段类型"""
    DAY_SESSION = "day"       # 日盘
    NIGHT_SESSION = "night"   # 夜盘
    NO_SESSION = "none"       # 无夜盘


@dataclass
class TradingSession:
    """交易时段定义"""
    day_open: time      # 日盘开盘时间
    day_close: time     # 日盘收盘时间
    night_open: time    # 夜盘开盘时间（可为None）
    night_close: time   # 夜盘结束时间（可为None）
    
    def has_night_session(self) -> bool:
        return self.night_open is not None and self.night_close is not None


# 各交易所/品种交易时间配置
# 时间格式：HH:MM:SS
TRADING_SESSIONS: Dict[str, TradingSession] = {
    # 上海期货交易所 (SHFE)
    "SHFE": TradingSession(
        day_open=time(9, 0),
        day_close=time(15, 0),
        night_open=time(21, 0),
        night_close=time(2, 30),  # 次日凌晨2:30
    ),
    
    # 大连商品交易所 (DCE)
    "DCE": TradingSession(
        day_open=time(9, 0),
        day_close=time(15, 0),
        night_open=time(21, 0),
        night_close=time(23, 30),  # 夜盘23:30结束
    ),
    
    # 郑州商品交易所 (CZCE)
    "CZCE": TradingSession(
        day_open=time(9, 0),
        day_close=time(15, 0),
        night_open=time(21, 0),
        night_close=time(23, 30),  # 夜盘23:30结束
    ),
    
    # 中金所 (CFFEX) - 国债期货无夜盘
    "CFFEX": TradingSession(
        day_open=time(9, 15),
        day_close=time(15, 0),
        night_open=None,
        night_close=None,
    ),
}

# 无夜盘品种列表
NO_NIGHT_SESSION_CONTRACTS = {
    # 农产品
    "c", "cs",     # 玉米、玉米淀粉
    "a", "b",      # 大豆
    "m", "y", "p", # 豆粕、豆油、棕榈油
    "rm", "oi", "cf", "sr", "ta", "ma", "sf", "sm", "wh", "pm",
    # 股指期货
    "IF", "IH", "IC", "IM",
    # 国债期货
    "T", "TF", "TS",
}

# 各品种所属交易所
CONTRACT_EXCHANGES: Dict[str, str] = {
    # 螺纹钢、热轧卷板
    "rb": "SHFE", "hc": "SHFE",
    # 铜、铝、锌、镍、锡
    "cu": "SHFE", "al": "SHFE", "zn": "SHFE", "ni": "SHFE", "sn": "SHFE", "pb": "SHFE",
    # 黄金、白银
    "au": "SHFE", "ag": "SHFE",
    # 橡胶
    "ru": "SHFE", "nr": "SHFE",
    # 沥青
    "bu": "SHFE", "sc": "SHFE",
    
    # 铁矿石、焦煤、焦炭、钢材
    "i": "DCE", "jm": "DCE", "j": "DCE", "l": "DCE", "v": "DCE", "pp": "DCE", "eg": "DCE", "eb": "DCE",
    # 豆粕、豆油、棕榈油
    "m": "DCE", "y": "DCE", "p": "DCE",
    # 大豆、玉米
    "a": "DCE", "b": "DCE", "c": "DCE", "cs": "DCE",
    # 鸡蛋、生猪
    "jd": "DCE", "lh": "DCE",
    
    # 棉花、白糖、PTA、甲醇、硅铁、锰硅
    "cf": "CZCE", "sr": "CZCE", "ta": "CZCE", "ma": "CZCE", "sf": "CZCE", "sm": "CZCE",
    # 菜粕、菜油、玻璃
    "rm": "CZCE", "oi": "CZCE", "fg": "CZCE",
    # 白糖、普麦、强麦、早籼、晚籼、粳稻
    "WH": "CZCE", "PM": "CZCE", "WS": "CZCE", "WR": "CZCE", "ER": "CZCE",
    
    # 股指期货
    "IF": "CFFEX", "IH": "CFFEX", "IC": "CFFEX", "IM": "CFFEX",
    # 国债期货
    "T": "CFFEX", "TF": "CFFEX", "TS": "CFFEX",
}


def get_trading_session(symbol: str) -> TradingSession:
    """获取合约的交易时段"""
    exchange = CONTRACT_EXCHANGES.get(symbol.upper())
    if exchange and exchange in TRADING_SESSIONS:
        return TRADING_SESSIONS[exchange]
    
    # 默认返回SHFE的交易时间
    return TRADING_SESSIONS["SHFE"]


def is_night_session_contract(symbol: str) -> bool:
    """判断合约是否有夜盘"""
    if symbol.lower() in NO_NIGHT_SESSION_CONTRACTS:
        return False
    return True


def normalize_night_session_datetime(dt: datetime, symbol: str) -> Tuple[datetime, bool]:
    """
    将夜盘时间规整到正确的交易日。
    
    中国期货规则：
    - 夜盘 21:00-23:59 → 当日交易日
    - 夜盘 00:00-02:30 → 次日交易日（归入次日）
    
    Args:
        dt: 待处理的datetime对象
        symbol: 合约代码
        
    Returns:
        (规整后的datetime, 是否为夜盘数据)
    """
    session = get_trading_session(symbol)
    
    if not session.has_night_session():
        return dt, False
    
    night_start = datetime.combine(dt.date(), session.night_open)
    # 处理跨日夜盘（如21:00-次日02:30）
    if session.night_close < session.night_open:
        # 夜盘跨日
        night_end = datetime.combine(dt.date() + timedelta(days=1), session.night_close)
    else:
        night_end = datetime.combine(dt.date(), session.night_close)
    
    # 判断是否在夜盘时段
    if dt.hour >= 21 or dt.hour < session.night_close.hour:
        # 属于夜盘，需要归入次日
        if dt.hour >= 21:
            # 21:00-23:59 归入次日
            normalized_date = dt.date() + timedelta(days=1)
        else:
            # 00:00-02:30 归入次日
            normalized_date = dt.date() + timedelta(days=1)
        
        normalized_dt = datetime.combine(normalized_date, dt.time())
        return normalized_dt, True
    
    return dt, False


def normalize_night_session_df(df: pd.DataFrame, symbol: str, datetime_col: str = "date") -> pd.DataFrame:
    """
    将DataFrame中的夜盘时间规整到正确交易日。
    
    Args:
        df: 包含datetime列的DataFrame
        symbol: 合约代码
        datetime_col: datetime列的列名
        
    Returns:
        处理后的DataFrame（已规整交易日）
    """
    df = df.copy()
    
    if datetime_col not in df.columns:
        return df
    
    # 解析datetime
    if df[datetime_col].dtype == 'object':
        df[datetime_col] = pd.to_datetime(df[datetime_col])
    
    # 规整夜盘时间
    def normalize_row(dt):
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        return normalize_night_session_datetime(dt, symbol)[0]
    
    df[datetime_col] = df[datetime_col].apply(normalize_row)
    
    # 按日期分组聚合（同一交易日的多根bar合并）
    # 这里保留原样，具体聚合逻辑在后续处理
    
    return df


def filter_trading_hours(
    df: pd.DataFrame,
    symbol: str,
    datetime_col: str = "date",
    include_hours: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    过滤非交易时段的数据。
    
    Args:
        df: DataFrame
        symbol: 合约代码
        datetime_col: datetime列名
        include_hours: 指定保留的小时列表（如 [9, 10, 13, 14] 表示只保留9-10点和13-14点）
        
    Returns:
        过滤后的DataFrame
    """
    df = df.copy()
    
    if datetime_col not in df.columns:
        return df
    
    if df[datetime_col].dtype == 'object':
        df[datetime_col] = pd.to_datetime(df[datetime_col])
    
    session = get_trading_session(symbol)
    
    if include_hours is not None:
        # 保留指定小时的数据
        df = df[df[datetime_col].dt.hour.isin(include_hours)]
    else:
        # 保留交易时段的数据
        trading_hours = []
        
        # 日盘时段
        day_start = session.day_open.hour
        day_end = session.day_close.hour
        trading_hours.extend(range(day_start, day_end + 1))
        
        # 夜盘时段
        if session.has_night_session():
            night_hours = []
            # 21:00-23:59
            night_hours.extend(range(session.night_open.hour, 24))
            # 00:00-02:30
            night_hours.extend(range(0, session.night_close.hour + 1))
            trading_hours.extend(night_hours)
        
        df = df[df[datetime_col].dt.hour.isin(trading_hours)]
    
    return df


def get_continuous_trading_dates(
    start_date: datetime,
    end_date: datetime,
    symbol: str
) -> List[datetime]:
    """
    获取连续的交易日列表（排除非交易日）。
    
    注意：中国期货周末休市（周六、周日），但可能因节假日调整。
    此函数按自然日生成，假设周末休市。
    """
    dates = []
    current = start_date
    
    while current <= end_date:
        # 排除周六(5)、周日(6)
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    
    return dates


@dataclass
class SessionInfo:
    """交易时段信息"""
    is_trading_day: bool
    has_night_session: bool
    day_session: Tuple[datetime, datetime]  # (开盘, 收盘)
    night_session: Optional[Tuple[datetime, datetime]]  # 可为None
    trading_date: datetime  # 规整后的交易日


def get_session_info(dt: datetime, symbol: str) -> SessionInfo:
    """
    获取指定时间的交易时段信息。
    
    Args:
        dt: datetime对象
        symbol: 合约代码
        
    Returns:
        SessionInfo对象
    """
    session = get_trading_session(symbol)
    normalized_dt, is_night = normalize_night_session_datetime(dt, symbol)
    trading_date = normalized_dt.date() if isinstance(normalized_dt, datetime) else normalized_dt
    
    # 构建日盘时段
    day_start = datetime.combine(trading_date, session.day_open)
    day_end = datetime.combine(trading_date, session.day_close)
    
    # 构建夜盘时段（如果存在）
    night_session = None
    if session.has_night_session():
        # 夜盘21:00开始，归属当日
        night_start = datetime.combine(trading_date, session.night_open)
        # 夜盘结束时间可能跨日
        if session.night_close < session.night_open:
            night_end = datetime.combine(trading_date + timedelta(days=1), session.night_close)
        else:
            night_end = datetime.combine(trading_date, session.night_close)
        night_session = (night_start, night_end)
    
    return SessionInfo(
        is_trading_day=trading_date.weekday() < 5,
        has_night_session=session.has_night_session(),
        day_session=(day_start, day_end),
        night_session=night_session,
        trading_date=datetime.combine(trading_date, time(0, 0))
    )


def is_valid_trading_time(dt: datetime, symbol: str) -> bool:
    """
    判断给定时间是否为交易时段。
    
    Args:
        dt: datetime对象
        symbol: 合约代码
        
    Returns:
        是否为交易时段
    """
    info = get_session_info(dt, symbol)
    
    if not info.is_trading_day:
        return False
    
    if info.day_session[0] <= dt <= info.day_session[1]:
        return True
    
    if info.night_session and info.night_session[0] <= dt <= info.night_session[1]:
        return True
    
    return False


def create_trading_calendar(
    start_date: datetime,
    end_date: datetime,
    symbol: str
) -> pd.DataFrame:
    """
    创建交易日历，包含每个交易日的交易时段信息。
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        symbol: 合约代码
        
    Returns:
        包含交易日历的DataFrame
    """
    records = []
    current = start_date
    
    while current <= end_date:
        info = get_session_info(current, symbol)
        
        records.append({
            "date": current.date(),
            "is_trading_day": info.is_trading_day,
            "has_night_session": info.has_night_session,
            "day_session_start": info.day_session[0] if info.day_session else None,
            "day_session_end": info.day_session[1] if info.day_session else None,
            "night_session_start": info.night_session[0] if info.night_session else None,
            "night_session_end": info.night_session[1] if info.night_session else None,
        })
        
        current += timedelta(days=1)
    
    return pd.DataFrame(records)
