"""
Order and Position Definitions

Defines the core data structures for trading orders and positions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Literal
from decimal import Decimal


class Direction(Enum):
    """Trade direction."""
    LONG = "Long"    # 多头（买入）
    SHORT = "Short"  # 空头（卖出）


class OrderPurpose(Enum):
    """Order purpose - distinguishes opening vs closing."""
    OPEN = "Open"      # 开仓
    CLOSE = "Close"    # 平仓


class OrderType(Enum):
    """Order type."""
    MARKET = "Market"      # 市价单
    LIMIT = "Limit"        # 限价单


class OrderStatus(Enum):
    """Order status."""
    PENDING = "Pending"        # 待成交
    PARTIAL = "Partial"       # 部分成交
    FILLED = "Filled"         # 全部成交
    CANCELLED = "Cancelled"    # 已取消
    REJECTED = "Rejected"      # 已拒绝


class PositionSide(Enum):
    """Position side."""
    LONG = "Long"      # 多头持仓
    SHORT = "Short"    # 空头持仓
    FLAT = "Flat"      # 空仓（无持仓）


@dataclass
class Order:
    """
    Trading order structure.
    
    Format: DIRECTION|ORDER_TYPE|VOLUME|SYMBOL|PRICE
    Example: LONG|MARKET|10|rb0|3500.0
    """
    direction: Direction
    order_type: OrderType
    volume: int                          # 交易手数
    symbol: str                          # 合约代码 (如 rb0, hc0)
    price: Optional[float] = None        # 限价价格 (市价单为 None)
    exchange: Optional[str] = None       # 交易所代码 (SHFE, DCE, CZCE)
    
    purpose: OrderPurpose = OrderPurpose.OPEN  # 开仓或平仓
    
    order_id: str = ""                   # 订单ID
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0           # 成交价格
    filled_volume: int = 0               # 已成交手数
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    
    # 原始信号来源
    signal_source: str = ""             # 信号来源 (e.g., "Trader Agent", "Manual")
    raw_signal: str = ""               # 原始信号内容
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"{self.symbol}_{int(datetime.now().timestamp() * 1000)}"
    
    @property
    def remaining_volume(self) -> int:
        """剩余未成交手数"""
        return self.volume - self.filled_volume
    
    @property
    def is_completed(self) -> bool:
        """订单是否完成"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "direction": self.direction.value,
            "purpose": self.purpose.value,
            "order_type": self.order_type.value,
            "volume": self.volume,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "price": self.price,
            "status": self.status.value,
            "filled_price": self.filled_price,
            "filled_volume": self.filled_volume,
            "create_time": self.create_time.isoformat(),
        }
    
    @classmethod
    def from_signal_string(cls, signal: str, symbol: str, exchange: str = "SHFE") -> "Order":
        """
        从信号字符串解析订单。
        
        信号格式: ACTION|VOLUME|PRICE
        Example: BUY|10|3500.0 -> LONG, MARKET(if price None), 10 lots
        Example: SELL|5|3400.0 -> SHORT, LIMIT, 5 lots
        
        ACTION: BUY (开多), SELL (开空), CLOSE_LONG (平多), CLOSE_SHORT (平空)
        """
        parts = signal.upper().strip().split("|")
        if len(parts) < 1:
            raise ValueError(f"Invalid signal format: {signal}")
        
        action = parts[0].strip()
        volume = int(parts[1]) if len(parts) > 1 else 1
        price = float(parts[2]) if len(parts) > 2 else None
        
        # 解析方向和订单类型
        if action == "BUY":
            direction = Direction.LONG
            purpose = OrderPurpose.OPEN
            order_type = OrderType.MARKET if price is None else OrderType.LIMIT
        elif action == "SELL":
            direction = Direction.SHORT
            purpose = OrderPurpose.OPEN
            order_type = OrderType.MARKET if price is None else OrderType.LIMIT
        elif action == "CLOSE_LONG":
            direction = Direction.SHORT  # 平多 = 卖出 = 空头方向
            purpose = OrderPurpose.CLOSE
            order_type = OrderType.MARKET
        elif action == "CLOSE_SHORT":
            direction = Direction.LONG   # 平空 = 买入 = 多头方向
            purpose = OrderPurpose.CLOSE
            order_type = OrderType.MARKET
        else:
            raise ValueError(f"Unknown action: {action}")
        
        return cls(
            direction=direction,
            purpose=purpose,
            order_type=order_type,
            volume=volume,
            symbol=symbol,
            price=price,
            exchange=exchange,
            raw_signal=signal,
        )
    
    def __str__(self) -> str:
        price_str = f"{self.price}" if self.price else "MARKET"
        return f"Order({self.direction.value}|{self.order_type.value}|{self.volume}|{self.symbol}|{price_str})"


@dataclass
class Position:
    """
    Position structure.
    
    Represents a held position in a futures contract.
    """
    symbol: str
    exchange: Optional[str] = None
    side: PositionSide = PositionSide.FLAT
    
    # 持仓信息
    volume: int = 0               # 持仓手数
    open_price: float = 0.0      # 开仓均价
    current_price: float = 0.0   # 当前价格
    settlement_price: float = 0.0 # 结算价
    
    # 合约信息
    contract_multiplier: float = 10.0   # 合约乘数 (螺纹钢10吨/手)
    margin_ratio: float = 0.12         # 保证金比例 (12%)
    tick_size: float = 1.0             # 最小变动价位
    
    # 关联订单
    open_order_id: str = ""
    close_order_id: str = ""
    
    def __post_init__(self):
        if self.exchange is None:
            self.exchange = self._infer_exchange()
    
    def _infer_exchange(self) -> str:
        """根据合约代码推断交易所"""
        symbol_upper = self.symbol.upper()
        if symbol_upper.startswith("RB") or symbol_upper.startswith("HC") or \
           symbol_upper.startswith("CU") or symbol_upper.startswith("AU") or \
           symbol_upper.startswith("AG") or symbol_upper.startswith("ZN"):
            return "SHFE"
        elif symbol_upper.startswith("I") or symbol_upper.startswith("M") or \
             symbol_upper.startswith("Y") or symbol_upper.startswith("P"):
            return "DCE"
        elif symbol_upper.startswith("CF") or symbol_upper.startswith("SR") or \
             symbol_upper.startswith("TA") or symbol_upper.startswith("RM"):
            return "CZCE"
        return "UNKNOWN"
    
    @property
    def market_value(self) -> float:
        """市值（按当前价格计算）"""
        return self.volume * self.current_price * self.contract_multiplier
    
    @property
    def open_cost(self) -> float:
        """开仓成本"""
        return self.volume * self.open_price * self.contract_multiplier
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        if self.side == PositionSide.LONG:
            return (self.current_price - self.open_price) * self.volume * self.contract_multiplier
        elif self.side == PositionSide.SHORT:
            return (self.open_price - self.current_price) * self.volume * self.contract_multiplier
        return 0.0
    
    @property
    def realized_pnl(self) -> float:
        """已实现盈亏"""
        # This would be calculated on close
        return 0.0
    
    @property
    def margin_required(self) -> float:
        """所需保证金"""
        return self.volume * self.current_price * self.contract_multiplier * self.margin_ratio
    
    @property
    def position_value(self) -> float:
        """持仓价值"""
        return self.volume * self.open_price * self.contract_multiplier
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side.value,
            "volume": self.volume,
            "open_price": self.open_price,
            "current_price": self.current_price,
            "margin_required": self.margin_required,
            "unrealized_pnl": self.unrealized_pnl,
            "market_value": self.market_value,
        }
    
    def __str__(self) -> str:
        return f"Position({self.symbol}|{self.side.value}|{self.volume}|O:{self.open_price}|C:{self.current_price}|PnL:{self.unrealized_pnl:.2f})"
