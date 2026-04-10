"""
Risk Manager Module

Handles margin calculation, position sizing, and risk control
to prevent liquidation (爆仓).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal


@dataclass
class AccountInfo:
    """Account information."""
    account_id: str = "PAPER_ACCOUNT"
    balance: float = 1000000.0          # 账户余额 (100万)
    available_balance: float = 1000000.0  # 可用资金
    frozen_margin: float = 0.0         # 冻结保证金
    realized_pnl: float = 0.0          # 已实现盈亏
    unrealized_pnl: float = 0.0        # 未实现盈亏
    total_assets: float = 1000000.0   # 总资产
    risk_ratio: float = 0.0            # 风险度
    
    # 风控参数
    max_leverage: float = 10.0        # 最大杠杆倍数
    max_position_ratio: float = 0.3   # 最大持仓比例 (30%)
    warning_margin_ratio: float = 0.8  # 预警保证金比例 (20% 强平)
    force_close_ratio: float = 0.5     # 强平保证金比例
    
    def update(self):
        """更新账户状态"""
        self.total_assets = self.balance + self.realized_pnl + self.unrealized_pnl
        self.available_balance = self.total_assets - self.frozen_margin
        if self.total_assets > 0:
            self.risk_ratio = self.frozen_margin / self.total_assets
    
    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "balance": self.balance,
            "available_balance": self.available_balance,
            "frozen_margin": self.frozen_margin,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_assets": self.total_assets,
            "risk_ratio": self.risk_ratio,
        }


class RiskManager:
    """
    Risk management for futures trading.
    
    Calculates margin requirements, checks position limits,
    and prevents liquidation (爆仓).
    """
    
    # 期货合约保证金和乘数配置 (示例)
    CONTRACT_CONFIG = {
        # 螺纹钢
        "rb": {"multiplier": 10, "margin_ratio": 0.12, "tick_size": 1},
        # 热轧卷板
        "hc": {"multiplier": 10, "margin_ratio": 0.12, "tick_size": 1},
        # 铁矿石
        "i": {"multiplier": 100, "margin_ratio": 0.15, "tick_size": 0.5},
        # 焦煤
        "jm": {"multiplier": 60, "margin_ratio": 0.15, "tick_size": 0.5},
        # 焦炭
        "j": {"multiplier": 100, "margin_ratio": 0.15, "tick_size": 0.5},
        # 豆粕
        "m": {"multiplier": 10, "margin_ratio": 0.11, "tick_size": 1},
        # 豆油
        "y": {"multiplier": 10, "margin_ratio": 0.11, "tick_size": 2},
        # 棕榈油
        "p": {"multiplier": 10, "margin_ratio": 0.11, "tick_size": 2},
        # 黄金
        "au": {"multiplier": 1000, "margin_ratio": 0.10, "tick_size": 0.05},
        # 白银
        "ag": {"multiplier": 15, "margin_ratio": 0.12, "tick_size": 1},
        # 铜
        "cu": {"multiplier": 5, "margin_ratio": 0.12, "tick_size": 10},
        # 铝
        "al": {"multiplier": 5, "margin_ratio": 0.11, "tick_size": 5},
        # 锌
        "zn": {"multiplier": 5, "margin_ratio": 0.11, "tick_size": 5},
        # 原油
        "sc": {"multiplier": 1000, "margin_ratio": 0.10, "tick_size": 0.1},
        # 沥青
        "bu": {"multiplier": 10, "margin_ratio": 0.11, "tick_size": 2},
    }
    
    def __init__(self, initial_balance: float = 1000000.0, config: Optional[Dict] = None):
        self.account = AccountInfo(balance=initial_balance, available_balance=initial_balance)
        self.config = config or {}
        self._update_config()
    
    def _update_config(self):
        """更新配置"""
        if "max_leverage" in self.config:
            self.account.max_leverage = self.config["max_leverage"]
        if "max_position_ratio" in self.config:
            self.account.max_position_ratio = self.config["max_position_ratio"]
        if "warning_margin_ratio" in self.config:
            self.account.warning_margin_ratio = self.config["warning_margin_ratio"]
        if "force_close_ratio" in self.config:
            self.account.force_close_ratio = self.config["force_close_ratio"]
    
    def get_contract_config(self, symbol: str) -> Dict:
        """获取合约配置"""
        symbol_lower = symbol.lower()
        for key in self.CONTRACT_CONFIG:
            if symbol_lower.startswith(key):
                return self.CONTRACT_CONFIG[key].copy()
        # 默认配置
        return {"multiplier": 10, "margin_ratio": 0.12, "tick_size": 1}
    
    def calculate_margin(self, symbol: str, volume: int, price: float) -> float:
        """
        计算开仓所需保证金。
        
        公式: 保证金 = 手数 × 合约乘数 × 价格 × 保证金比例
        """
        config = self.get_contract_config(symbol)
        multiplier = config["multiplier"]
        margin_ratio = config["margin_ratio"]
        
        margin = volume * multiplier * price * margin_ratio
        return margin
    
    def calculate_max_volume(self, symbol: str, price: float) -> int:
        """
        计算最大可开仓手数。
        
        基于可用资金和最大持仓比例限制。
        """
        config = self.get_contract_config(symbol)
        multiplier = config["multiplier"]
        margin_ratio = config["margin_ratio"]
        
        # 基于可用资金计算
        margin_per_lot = multiplier * price * margin_ratio
        max_by_balance = int(self.account.available_balance / margin_per_lot)
        
        # 基于最大持仓比例计算
        max_by_ratio = int(self.account.total_assets * self.account.max_position_ratio / margin_per_lot)
        
        return min(max_by_balance, max_by_ratio)
    
    def check_open_position(self, symbol: str, volume: int, price: float) -> tuple:
        """
        检查是否可以开仓。
        
        Returns:
            (can_open: bool, reason: str, adjusted_volume: int)
        """
        # 计算所需保证金
        required_margin = self.calculate_margin(symbol, volume, price)
        
        # 检查资金是否充足
        if required_margin > self.account.available_balance:
            # 尝试调整手数
            max_vol = self.calculate_max_volume(symbol, price)
            if max_vol > 0:
                adjusted_margin = self.calculate_margin(symbol, max_vol, price)
                if adjusted_margin <= self.account.available_balance:
                    return True, f"Volume adjusted to {max_vol} lots", max_vol
            return False, "Insufficient margin", 0
        
        # 检查杠杆
        new_total_margin = self.account.frozen_margin + required_margin
        if new_total_margin > self.account.total_assets * self.account.max_leverage:
            # 尝试调整手数到杠杆限制内
            max_vol_by_lev = int(self.account.total_assets * self.account.max_leverage / 
                                 (self.get_contract_config(symbol)["multiplier"] * price * 
                                  self.get_contract_config(symbol)["margin_ratio"]))
            if max_vol_by_lev > 0:
                return True, f"Volume adjusted to {max_vol_by_lev} lots by leverage", max_vol_by_lev
            return False, "Exceeds maximum leverage", 0
        
        # 检查风险度 (持仓保证金占总资产的比例)
        new_risk = new_total_margin / self.account.total_assets
        if new_risk > self.account.max_position_ratio:
            # 尝试调整手数到风险限制内
            max_vol_by_risk = int(self.account.total_assets * self.account.max_position_ratio /
                                 (self.get_contract_config(symbol)["multiplier"] * price *
                                  self.get_contract_config(symbol)["margin_ratio"]))
            if max_vol_by_risk > 0:
                return True, f"Volume adjusted to {max_vol_by_risk} lots by risk limit", max_vol_by_risk
            return False, "Exceeds maximum position ratio", 0
        
        return True, "OK", volume
    
    def update_position_price(self, symbol: str, new_price: float):
        """更新持仓价格（用于计算浮动盈亏）"""
        pass  # Position updates are handled by PaperBroker
    
    def freeze_margin(self, amount: float):
        """冻结保证金"""
        self.account.frozen_margin += amount
        self.account.available_balance -= amount
        self.account.update()
    
    def release_margin(self, amount: float):
        """释放保证金"""
        self.account.frozen_margin -= amount
        self.account.available_balance += amount
        # If releasing more than frozen (all positions closed), clear unrealized PnL
        if self.account.frozen_margin < 0:
            self.account.unrealized_pnl = 0.0
            self.account.frozen_margin = 0.0
        self.account.update()
    
    def settle_trade(self, pnl: float):
        """结算交易盈亏"""
        if pnl >= 0:
            self.account.balance += pnl
            self.account.realized_pnl += pnl
        else:
            self.account.balance += pnl
            self.account.realized_pnl += pnl
        self.account.update()
    
    def update_unrealized_pnl(self, pnl: float):
        """更新未实现盈亏"""
        self.account.unrealized_pnl = pnl
        self.account.update()
    
    def get_account_summary(self) -> Dict:
        """获取账户摘要"""
        self.account.update()
        return self.account.to_dict()
    
    def check_force_close(self, positions: List) -> List[str]:
        """
        检查是否需要强平。
        
        Returns list of position symbols that should be force closed.
        """
        force_close_list = []
        
        for pos in positions:
            if pos.volume <= 0:
                continue
            
            config = self.get_contract_config(pos.symbol)
            margin_ratio = config["margin_ratio"]
            
            # 计算持仓盈亏
            pnl = pos.unrealized_pnl
            pos_value = pos.position_value
            
            # 计算保证金比例
            if pos_value > 0:
                margin_remain = (pos_value + pnl) / (pos.volume * config["multiplier"])
                margin_ratio_actual = margin_remain / pos.current_price
            else:
                continue
            
            # 如果保证金比例低于强平线
            if margin_ratio_actual < self.account.force_close_ratio:
                force_close_list.append(pos.symbol)
        
        return force_close_list


@dataclass
class MarginRequirement:
    """Margin requirement details for a position."""
    symbol: str
    side: str
    volume: int
    open_price: float
    current_price: float
    multiplier: float
    margin_ratio: float
    
    # Calculated fields
    margin_used: float = 0.0
    unrealized_pnl: float = 0.0
    margin_ratio_actual: float = 0.0
    
    def calculate(self):
        """执行计算"""
        self.margin_used = self.volume * self.multiplier * self.current_price * self.margin_ratio
        
        if self.side == "Long":
            self.unrealized_pnl = (self.current_price - self.open_price) * self.volume * self.multiplier
        else:
            self.unrealized_pnl = (self.open_price - self.current_price) * self.volume * self.multiplier
        
        # 实际保证金比例 = (持仓价值 + 盈亏) / (手数 × 乘数 × 当前价)
        if self.margin_used > 0:
            position_value = self.volume * self.multiplier * self.current_price
            self.margin_ratio_actual = (position_value + self.unrealized_pnl) / position_value
        
        return self
