"""
Position Manager

Manages open positions and calculates PnL.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from .order import Position, PositionSide, Direction


class PositionManager:
    """Manages all open positions and calculates PnL."""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # symbol -> Position
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """是否有持仓"""
        pos = self.positions.get(symbol)
        return pos is not None and pos.volume > 0
    
    def open_position(
        self,
        symbol: str,
        direction: Direction,
        volume: int,
        price: float,
        exchange: Optional[str] = None,
        order_id: str = "",
    ) -> Position:
        """
        开仓。
        
        如果已有反向持仓，则平仓后开新仓。
        """
        config = self._get_contract_config(symbol)
        
        if self.has_position(symbol):
            pos = self.positions[symbol]
            
            if pos.side == PositionSide.LONG and direction == Direction.SHORT:
                # 平多开空：先平多仓，再开空仓
                close_vol = min(pos.volume, volume)
                pnl = (price - pos.open_price) * close_vol * config["multiplier"]
                pos.volume -= close_vol
                
                if volume > close_vol:
                    # 开新空仓
                    new_volume = volume - close_vol
                    pos = Position(
                        symbol=symbol,
                        exchange=exchange,
                        side=PositionSide.SHORT,
                        volume=new_volume,
                        open_price=price,
                        current_price=price,
                        contract_multiplier=config["multiplier"],
                        margin_ratio=config["margin_ratio"],
                        open_order_id=order_id,
                    )
                    self.positions[symbol] = pos
                
                return pnl
                
            elif pos.side == PositionSide.SHORT and direction == Direction.LONG:
                # 平空开多
                close_vol = min(pos.volume, volume)
                pnl = (pos.open_price - price) * close_vol * config["multiplier"]
                pos.volume -= close_vol
                
                if volume > close_vol:
                    new_volume = volume - close_vol
                    pos = Position(
                        symbol=symbol,
                        exchange=exchange,
                        side=PositionSide.LONG,
                        volume=new_volume,
                        open_price=price,
                        current_price=price,
                        contract_multiplier=config["multiplier"],
                        margin_ratio=config["margin_ratio"],
                        open_order_id=order_id,
                    )
                    self.positions[symbol] = pos
                
                return pnl
        else:
            # 新开仓
            side = PositionSide.LONG if direction == Direction.LONG else PositionSide.SHORT
            pos = Position(
                symbol=symbol,
                exchange=exchange,
                side=side,
                volume=volume,
                open_price=price,
                current_price=price,
                contract_multiplier=config["multiplier"],
                margin_ratio=config["margin_ratio"],
                open_order_id=order_id,
            )
            self.positions[symbol] = pos
            return 0.0
        
        return 0.0
    
    def close_position(
        self,
        symbol: str,
        volume: int,
        price: float,
        order_id: str = "",
    ) -> float:
        """
        平仓。
        
        Returns: 平仓盈亏
        """
        if not self.has_position(symbol):
            return 0.0
        
        pos = self.positions[symbol]
        config = self._get_contract_config(symbol)
        
        if volume >= pos.volume:
            # 全部平仓
            if pos.side == PositionSide.LONG:
                pnl = (price - pos.open_price) * pos.volume * config["multiplier"]
            else:
                pnl = (pos.open_price - price) * pos.volume * config["multiplier"]
            
            pos.volume = 0
            pos.side = PositionSide.FLAT
            return pnl
        else:
            # 部分平仓
            if pos.side == PositionSide.LONG:
                pnl = (price - pos.open_price) * volume * config["multiplier"]
            else:
                pnl = (pos.open_price - price) * volume * config["multiplier"]
            
            pos.volume -= volume
            return pnl
    
    def update_prices(self, prices: Dict[str, float]):
        """批量更新持仓价格"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
    
    def get_all_positions(self) -> List[Position]:
        """获取所有持仓"""
        return [p for p in self.positions.values() if p.volume > 0]
    
    def get_total_unrealized_pnl(self) -> float:
        """计算总浮动盈亏"""
        total = 0.0
        for pos in self.get_all_positions():
            total += pos.unrealized_pnl
        return total
    
    def get_total_margin_required(self) -> float:
        """计算总保证金"""
        total = 0.0
        for pos in self.get_all_positions():
            total += pos.margin_required
        return total
    
    def _get_contract_config(self, symbol: str) -> Dict:
        """获取合约配置"""
        from .risk_manager import RiskManager
        return RiskManager.CONTRACT_CONFIG.get(
            symbol.lower().rstrip('0123456789'),
            {"multiplier": 10, "margin_ratio": 0.12}
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "positions": [p.to_dict() for p in self.get_all_positions()],
            "total_unrealized_pnl": self.get_total_unrealized_pnl(),
            "total_margin_required": self.get_total_margin_required(),
        }
