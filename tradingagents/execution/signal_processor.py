"""
Signal Processor

Processes trading signals from Trader Agent and converts them
to executable orders.
"""

from typing import Dict, Optional
from .order import Direction, OrderType


class SignalProcessor:
    """
    Processes trading signals and generates executable orders.
    
    Converts BUY/HOLD/SELL signals with position context into
    specific trading actions (OPEN LONG, CLOSE SHORT, etc.)
    """
    
    def __init__(self, default_volume: int = 1):
        self.default_volume = default_volume
        self.current_position: Dict[str, str] = {}  # symbol -> "Long" or "Short"
    
    def update_position(self, symbol: str, side: str):
        """Update known position state."""
        self.current_position[symbol] = side
    
    def clear_position(self, symbol: str):
        """Clear position state after closing."""
        if symbol in self.current_position:
            del self.current_position[symbol]
    
    def process_signal(
        self,
        signal: str,
        symbol: str,
        current_position: Optional[str] = None,
    ) -> tuple:
        """
        Process a trading signal and generate order parameters.
        
        Args:
            signal: Signal from Trader Agent ("BUY", "HOLD", "SELL")
            symbol: Contract symbol
            current_position: Current position side ("Long", "Short", or None)
            
        Returns:
            (action: str, volume: int, order_type: OrderType)
            action examples: "BUY_OPEN", "SELL_OPEN", "CLOSE_LONG", "CLOSE_SHORT"
        """
        if current_position is None:
            current_position = self.current_position.get(symbol, None)
        
        signal = signal.strip().upper()
        
        if signal == "BUY":
            if current_position == "Long":
                # Already long, could add position
                return ("BUY_OPEN", self.default_volume, OrderType.MARKET)
            elif current_position == "Short":
                # Reverse position: close short, open long
                return ("CLOSE_SHORT", self.default_volume, OrderType.MARKET)
            else:
                # No position, open long
                return ("BUY_OPEN", self.default_volume, OrderType.MARKET)
        
        elif signal == "SELL":
            if current_position == "Short":
                # Already short, could add position
                return ("SELL_OPEN", self.default_volume, OrderType.MARKET)
            elif current_position == "Long":
                # Reverse position: close long, open short
                return ("CLOSE_LONG", self.default_volume, OrderType.MARKET)
            else:
                # No position, open short
                return ("SELL_OPEN", self.default_volume, OrderType.MARKET)
        
        elif signal == "HOLD":
            return ("HOLD", 0, OrderType.MARKET)
        
        elif signal == "CLOSE_LONG":
            return ("CLOSE_LONG", self.default_volume, OrderType.MARKET)
        
        elif signal == "CLOSE_SHORT":
            return ("CLOSE_SHORT", self.default_volume, OrderType.MARKET)
        
        else:
            return ("UNKNOWN", 0, OrderType.MARKET)
    
    def signal_to_order_format(self, signal: str) -> str:
        """
        Convert signal to order format string.
        
        Args:
            signal: "BUY", "HOLD", "SELL"
            
        Returns:
            Order string like "BUY|10|MARKET"
        """
        action, volume, _ = self.process_signal(signal, "")
        if action in ["BUY_OPEN", "CLOSE_SHORT"]:
            return f"BUY|{volume}|MARKET"
        elif action in ["SELL_OPEN", "CLOSE_LONG"]:
            return f"SELL|{volume}|MARKET"
        elif action == "HOLD":
            return "HOLD|0|MARKET"
        else:
            return f"UNKNOWN|0|MARKET"
