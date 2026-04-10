"""
Paper Broker (撮合引擎)

A lightweight order matching engine for paper trading.
Supports both in-memory and SQLite persistence.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict

from .order import Order, OrderType, Direction, OrderStatus, OrderPurpose
from .position import PositionManager
from .risk_manager import RiskManager


@dataclass
class TradeRecord:
    """成交记录"""
    trade_id: str
    order_id: str
    symbol: str
    direction: str
    volume: int
    price: float
    commission: float
    trade_time: str
    pnl: float = 0.0  # 平仓盈亏（仅平仓时）


class PaperBroker:
    """
    Paper Trading Broker (模拟撮合引擎).
    
    Features:
    - Order matching based on current market prices
    - Position management
    - Margin calculation and risk control
    - SQLite persistence (optional)
    - Real-time PnL calculation
    """
    
    def __init__(
        self,
        initial_balance: float = 1000000.0,
        db_path: Optional[str] = None,
        commission_rate: float = 0.0003,
    ):
        """
        Initialize Paper Broker.
        
        Args:
            initial_balance: Initial account balance (default 1M)
            db_path: SQLite database path (None for in-memory)
            commission_rate: Commission rate (0.03% default)
        """
        self.initial_balance = initial_balance
        self.db_path = db_path
        self.commission_rate = commission_rate
        
        # Core components
        self.risk_manager = RiskManager(initial_balance=initial_balance)
        self.position_manager = PositionManager()
        
        # Order book
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # Trade records
        self.trades: List[TradeRecord] = []
        
        # Price cache
        self.current_prices: Dict[str, float] = {}
        self.last_prices: Dict[str, float] = {}
        
        # Callbacks
        self.on_order_update: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        if db_path:
            self._init_db()
        
        # Get latest prices from akshare
        self._fetch_latest_prices()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                direction TEXT,
                order_type TEXT,
                volume INTEGER,
                symbol TEXT,
                exchange TEXT,
                price REAL,
                status TEXT,
                filled_price REAL,
                filled_volume INTEGER,
                create_time TEXT,
                update_time TEXT
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                order_id TEXT,
                symbol TEXT,
                direction TEXT,
                volume INTEGER,
                price REAL,
                commission REAL,
                trade_time TEXT,
                pnl REAL
            )
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                exchange TEXT,
                side TEXT,
                volume INTEGER,
                open_price REAL,
                current_price REAL,
                update_time TEXT
            )
        """)
        
        # Account table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance REAL,
                frozen_margin REAL,
                realized_pnl REAL,
                unrealized_pnl REAL,
                update_time TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _fetch_latest_prices(self):
        """Fetch latest prices from akshare"""
        try:
            from ..dataflows.akshare_futures import (
                get_main_contract_code,
                get_futures_daily_bars,
            )
            from datetime import timedelta
            
            for symbol in self.current_prices.keys():
                try:
                    main_contract = get_main_contract_code(symbol.lower().rstrip('0123456789'))
                    today = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                    bars_data = get_futures_daily_bars(main_contract, start_date, today)
                    
                    # Parse last price from bars data
                    lines = bars_data.strip().split('\n')
                    for line in reversed(lines):
                        if line and not line.startswith('#') and ',' in line:
                            parts = line.split(',')
                            if len(parts) >= 5:
                                self.last_prices[symbol] = float(parts[4])  # close price
                                self.current_prices[symbol] = float(parts[4])
                                break
                except Exception:
                    pass
        except Exception:
            pass
    
    def set_price(self, symbol: str, price: float):
        """Set current market price for a symbol"""
        with self._lock:
            self.current_prices[symbol] = price
            self.position_manager.update_prices({symbol: price})
            
            # Update risk manager
            self.risk_manager.update_unrealized_pnl(
                self.position_manager.get_total_unrealized_pnl()
            )
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        return self.current_prices.get(symbol)
    
    def submit_order(
        self,
        direction: Direction,
        purpose: OrderPurpose,
        order_type: OrderType,
        volume: int,
        symbol: str,
        price: Optional[float] = None,
        exchange: Optional[str] = None,
        signal_source: str = "Manual",
        raw_signal: str = "",
    ) -> Order:
        """
        Submit a trading order.
        
        Args:
            direction: LONG (多头) or SHORT (空头)
            purpose: OPEN (开仓) or CLOSE (平仓)
            order_type: MARKET or LIMIT
            volume: Number of lots
            symbol: Contract symbol (e.g., 'rb0')
            price: Limit price (None for market order)
            exchange: Exchange code
            signal_source: Source of the trading signal
            raw_signal: Raw signal content
            
        Returns:
            Order object with order_id
        """
        with self._lock:
            # Get current price
            current_price = self.current_prices.get(symbol)
            if current_price is None:
                self._fetch_latest_prices()
                current_price = self.current_prices.get(symbol)
            
            if current_price is None and price is None:
                raise ValueError(f"No price available for {symbol}")
            
            # Determine execution price
            exec_price = price if price else current_price
            
            # Create order
            order = Order(
                direction=direction,
                purpose=purpose,
                order_type=order_type,
                volume=volume,
                symbol=symbol,
                price=price,
                exchange=exchange,
                signal_source=signal_source,
                raw_signal=raw_signal,
            )
            
            # Check risk
            if purpose == OrderPurpose.OPEN:
                # Opening position
                can_open, reason, adj_vol = self.risk_manager.check_open_position(
                    symbol, volume, exec_price
                )
                if not can_open:
                    order.status = OrderStatus.REJECTED
                    order.update_time = datetime.now()
                    self.orders[order.order_id] = order
                    self.order_history.append(order)
                    return order
                
                if adj_vol < volume:
                    # Volume reduced due to risk limits
                    order.volume = adj_vol
                    order.update_time = datetime.now()
            else:
                # Closing position - check if we have position to close
                if not self.position_manager.has_position(symbol):
                    order.status = OrderStatus.REJECTED
                    order.update_time = datetime.now()
                    self.orders[order.order_id] = order
                    self.order_history.append(order)
                    return order
            
            # Submit for execution
            self.orders[order.order_id] = order
            
            # Execute immediately for market orders
            if order_type == OrderType.MARKET:
                self._execute_order(order, exec_price)
            
            self.order_history.append(order)
            
            # Callback
            if self.on_order_update:
                self.on_order_update(order)
            
            return order
    
    def _execute_order(self, order: Order, price: float):
        """Execute an order at given price"""
        # Calculate commission
        config = self.risk_manager.get_contract_config(order.symbol)
        commission = order.volume * config["multiplier"] * price * self.commission_rate
        
        # Update order
        order.filled_price = price
        order.filled_volume = order.volume
        order.status = OrderStatus.FILLED
        order.update_time = datetime.now()
        
        # Create trade record
        trade = TradeRecord(
            trade_id=f"T{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            direction=order.direction.value,
            volume=order.volume,
            price=price,
            commission=commission,
            trade_time=datetime.now().isoformat(),
        )
        self.trades.append(trade)
        
        # Update position
        if order.purpose == OrderPurpose.OPEN:
            # Opening position
            margin = self.risk_manager.calculate_margin(
                order.symbol, order.volume, price
            )
            self.risk_manager.freeze_margin(margin)
            self.position_manager.open_position(
                symbol=order.symbol,
                direction=order.direction,
                volume=order.volume,
                price=price,
                exchange=order.exchange,
                order_id=order.order_id,
            )
        else:
            # Closing position
            pnl = self.position_manager.close_position(
                symbol=order.symbol,
                volume=order.volume,
                price=price,
                order_id=order.order_id,
            )
            trade.pnl = pnl
            
            # Release margin and settle PnL
            config = self.risk_manager.get_contract_config(order.symbol)
            margin_release = order.volume * config["multiplier"] * price * config["margin_ratio"]
            self.risk_manager.release_margin(margin_release)
            self.risk_manager.settle_trade(pnl - commission)
        
        # Callback
        if self.on_trade:
            self.on_trade(trade)
    
    def close_long(self, symbol: str, volume: int, price: Optional[float] = None) -> Order:
        """平多仓"""
        return self.submit_order(
            direction=Direction.SHORT,  # 平多 = 卖出
            purpose=OrderPurpose.CLOSE,
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
            volume=volume,
            symbol=symbol,
            price=price,
        )
    
    def close_short(self, symbol: str, volume: int, price: Optional[float] = None) -> Order:
        """平空仓"""
        return self.submit_order(
            direction=Direction.LONG,   # 平空 = 买入
            purpose=OrderPurpose.CLOSE,
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
            volume=volume,
            symbol=symbol,
            price=price,
        )
    
    def buy_open(self, symbol: str, volume: int, price: Optional[float] = None) -> Order:
        """开多仓 (买入)"""
        return self.submit_order(
            direction=Direction.LONG,
            purpose=OrderPurpose.OPEN,
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
            volume=volume,
            symbol=symbol,
            price=price,
        )
    
    def sell_open(self, symbol: str, volume: int, price: Optional[float] = None) -> Order:
        """开空仓 (卖出)"""
        return self.submit_order(
            direction=Direction.SHORT,
            purpose=OrderPurpose.OPEN,
            order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
            volume=volume,
            symbol=symbol,
            price=price,
        )
    
    def process_signal(self, signal: str, symbol: str, exchange: str = "SHFE") -> Order:
        """
        Process a trading signal string.
        
        Signal format: ACTION|VOLUME|PRICE
        Example: BUY|10|3500.0, SELL|5|, CLOSE_LONG|3|
        """
        order = Order.from_signal_string(signal, symbol, exchange)
        return self.submit_order(
            direction=order.direction,
            order_type=order.order_type,
            volume=order.volume,
            symbol=symbol,
            price=order.price,
            exchange=exchange,
            signal_source="SignalProcessor",
            raw_signal=signal,
        )
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        account = self.risk_manager.get_account_summary()
        account["positions"] = self.position_manager.to_dict()
        return account
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a symbol"""
        pos = self.position_manager.get_position(symbol)
        return pos.to_dict() if pos else None
    
    def get_all_positions(self) -> List[Dict]:
        """Get all positions"""
        return self.position_manager.to_dict()["positions"]
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        return [asdict(t) for t in self.trades]
    
    def save_state(self):
        """Save current state to database"""
        if not self.db_path:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save account
        account = self.risk_manager.account
        cursor.execute("""
            INSERT OR REPLACE INTO account (id, balance, frozen_margin, realized_pnl, unrealized_pnl, update_time)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (account.balance, account.frozen_margin, account.realized_pnl, 
              account.unrealized_pnl, datetime.now().isoformat()))
        
        # Save positions
        for pos in self.position_manager.get_all_positions():
            cursor.execute("""
                INSERT OR REPLACE INTO positions (symbol, exchange, side, volume, open_price, current_price, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pos.symbol, pos.exchange, pos.side.value, pos.volume, 
                  pos.open_price, pos.current_price, datetime.now().isoformat()))
        
        # Save orders
        for order in self.orders.values():
            cursor.execute("""
                INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order.order_id, order.direction.value, order.order_type.value,
                  order.volume, order.symbol, order.exchange, order.price,
                  order.status.value, order.filled_price, order.filled_volume,
                  order.create_time.isoformat(), order.update_time.isoformat()))
        
        conn.commit()
        conn.close()
    
    def load_state(self):
        """Load state from database"""
        if not self.db_path:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load account
        cursor.execute("SELECT * FROM account WHERE id = 1")
        row = cursor.fetchone()
        if row:
            self.risk_manager.account.balance = row[1]
            self.risk_manager.account.frozen_margin = row[2]
            self.risk_manager.account.realized_pnl = row[3]
            self.risk_manager.account.unrealized_pnl = row[4]
            self.risk_manager.account.update()
        
        conn.close()
    
    def print_status(self):
        """Print current broker status"""
        account = self.risk_manager.account
        
        print("\n" + "="*60)
        print("PAPER BROKER STATUS")
        print("="*60)
        print(f"Account Balance:     {account.balance:,.2f}")
        print(f"Available Balance:  {account.available_balance:,.2f}")
        print(f"Frozen Margin:      {account.frozen_margin:,.2f}")
        print(f"Realized PnL:       {account.realized_pnl:,.2f}")
        print(f"Unrealized PnL:     {account.unrealized_pnl:,.2f}")
        print(f"Total Assets:       {account.total_assets:,.2f}")
        print(f"Risk Ratio:         {account.risk_ratio:.2%}")
        print("-"*60)
        print("POSITIONS:")
        for pos in self.position_manager.get_all_positions():
            print(f"  {pos}")
        print("-"*60)
        print(f"Total Unrealized PnL: {self.position_manager.get_total_unrealized_pnl():,.2f}")
        print(f"Total Margin Required: {self.position_manager.get_total_margin_required():,.2f}")
        print("="*60)
    
    def __str__(self) -> str:
        account = self.risk_manager.account
        return f"PaperBroker(balance={account.balance:,.2f}, positions={len(self.position_manager.get_all_positions())})"
