#!/usr/bin/env python3
"""
Paper Broker Demo

Demonstrates how to use the Paper Broker for paper trading.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.execution import (
    PaperBroker,
    Order,
    Direction,
    OrderType,
    RiskManager,
)
from tradingagents.execution.signal_processor import SignalProcessor


def demo_basic_orders():
    """Demo: Basic order operations."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Order Operations")
    print("="*60)
    
    # Create broker with initial balance of 1M
    broker = PaperBroker(initial_balance=1000000.0)
    
    # Set current market price
    broker.set_price("rb0", 3500.0)
    
    # Open a long position (buy 10 lots)
    order1 = broker.buy_open(symbol="rb0", volume=10)
    print(f"\n[ORDER 1] {order1}")
    print(f"Status: {order1.status.value}")
    
    # Print broker status
    broker.print_status()
    
    # Price goes up
    broker.set_price("rb0", 3550.0)
    print(f"\n[PRICE UPDATE] rb0: 3500 -> 3550")
    
    broker.print_status()
    
    # Close position (sell)
    order2 = broker.close_long(symbol="rb0", volume=10)
    print(f"\n[ORDER 2] {order2}")
    
    broker.print_status()


def demo_signal_processing():
    """Demo: Signal processing."""
    print("\n" + "="*60)
    print("DEMO 2: Signal Processing")
    print("="*60)
    
    broker = PaperBroker(initial_balance=1000000.0)
    signal_processor = SignalProcessor(default_volume=5)
    
    broker.set_price("rb0", 3400.0)
    
    # Process BUY signal - use direct API
    action, volume, _ = signal_processor.process_signal("BUY", "rb0")
    print(f"\nSignal: BUY -> Action: {action}, Volume: {volume}")
    
    if action != "HOLD":
        if "OPEN" in action:
            if action == "BUY_OPEN":
                order = broker.buy_open("rb0", volume)
            elif action == "SELL_OPEN":
                order = broker.sell_open("rb0", volume)
            # Update position in signal processor
            signal_processor.update_position("rb0", "Long")
        elif "CLOSE" in action:
            if action == "CLOSE_LONG":
                order = broker.close_long("rb0", volume)
                signal_processor.update_position("rb0", "Flat")
            elif action == "CLOSE_SHORT":
                order = broker.close_short("rb0", volume)
                signal_processor.update_position("rb0", "Flat")
        print(f"Order executed: {order}")
    
    broker.print_status()
    
    # Process SELL signal (should close position since we have Long)
    # First update signal processor with current position
    pos = broker.get_position("rb0")
    if pos:
        signal_processor.update_position("rb0", pos["side"])
    
    action, volume, _ = signal_processor.process_signal("SELL", "rb0")
    print(f"\nSignal: SELL -> Action: {action}, Volume: {volume}")
    
    if action != "HOLD":
        if "OPEN" in action:
            if action == "BUY_OPEN":
                order = broker.buy_open("rb0", volume)
                signal_processor.update_position("rb0", "Long")
            elif action == "SELL_OPEN":
                order = broker.sell_open("rb0", volume)
                signal_processor.update_position("rb0", "Short")
        elif "CLOSE" in action:
            if action == "CLOSE_LONG":
                order = broker.close_long("rb0", volume)
                signal_processor.update_position("rb0", "Flat")
            elif action == "CLOSE_SHORT":
                order = broker.close_short("rb0", volume)
                signal_processor.update_position("rb0", "Flat")
        print(f"Order executed: {order}")
    
    broker.print_status()


def demo_risk_management():
    """Demo: Risk management."""
    print("\n" + "="*60)
    print("DEMO 3: Risk Management")
    print("="*60)
    
    broker = PaperBroker(initial_balance=100000.0)  # Smaller account
    
    broker.set_price("rb0", 3500.0)
    
    # Calculate max volume
    risk_mgr = broker.risk_manager
    max_vol = risk_mgr.calculate_max_volume("rb0", 3500.0)
    print(f"\nMax position volume for rb0 at 3500: {max_vol} lots")
    
    # Check if we can open
    can_open, reason, adj_vol = risk_mgr.check_open_position("rb0", 100, 3500.0)
    print(f"Can open 100 lots? {can_open} - {reason}")
    if not can_open:
        print(f"Suggested adjusted volume: {adj_vol} lots")
    
    # Try to open beyond limit
    order = broker.buy_open(symbol="rb0", volume=100)
    print(f"\nOrder result: {order.status.value}")
    
    # Open within limit
    order = broker.buy_open(symbol="rb0", volume=max_vol)
    print(f"Order result for {max_vol} lots: {order.status.value}")
    
    broker.print_status()


def demo_multiple_positions():
    """Demo: Multiple positions."""
    print("\n" + "="*60)
    print("DEMO 4: Multiple Positions")
    print("="*60)
    
    broker = PaperBroker(initial_balance=2000000.0)
    
    # Set prices
    broker.set_price("rb0", 3500.0)
    broker.set_price("hc0", 3800.0)
    
    # Open positions in multiple contracts
    broker.buy_open("rb0", volume=10)
    broker.sell_open("hc0", volume=5)
    
    print("\nPositions opened:")
    broker.print_status()
    
    # Update prices (trends move against us)
    broker.set_price("rb0", 3450.0)  # -50 points
    broker.set_price("hc0", 3850.0)  # +50 points
    
    print("\nAfter price changes:")
    broker.print_status()
    
    # Close positions
    broker.close_long("rb0", volume=10)
    broker.close_short("hc0", volume=5)
    
    print("\nAfter closing:")
    broker.print_status()


def demo_with_akshare_prices():
    """Demo: Using real prices from akshare."""
    print("\n" + "="*60)
    print("DEMO 5: Real Prices from AkShare")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    try:
        from tradingagents.dataflows.akshare_futures import (
            get_main_contract_code,
            get_futures_daily_bars,
        )
        
        symbol = "rb"
        trade_date = "2024-11-15"
        
        # Get main contract
        main_contract = get_main_contract_code(symbol)
        print(f"\nMain contract for {symbol}: {main_contract}")
        
        # Get recent bars
        start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")
        bars_data = get_futures_daily_bars(main_contract, start_date, trade_date)
        
        print(f"\nRecent bars (last 3 days):")
        lines = bars_data.strip().split('\n')
        data_lines = [l for l in lines if l and not l.startswith('#') and ',' in l]
        for line in data_lines[-3:]:
            print(f"  {line}")
        
        # Parse close price
        last_line = data_lines[-1]
        parts = last_line.split(',')
        close_price = float(parts[4])
        print(f"\nClose price: {close_price}")
        
        # Create broker and set price
        broker = PaperBroker(initial_balance=1000000.0)
        broker.set_price(main_contract, close_price)
        
        print(f"\nPaper Broker initialized with {main_contract} at {close_price}")
        
        # Open position
        broker.buy_open(main_contract, volume=5)
        
        broker.print_status()
        
    except Exception as e:
        print(f"\nDemo failed: {e}")
        print("(This is expected if network is unavailable)")


def demo_trading_cycle():
    """Demo: Complete trading cycle with simulated signals."""
    print("\n" + "="*60)
    print("DEMO 6: Complete Trading Cycle")
    print("="*60)
    
    broker = PaperBroker(initial_balance=1000000.0)
    signal_processor = SignalProcessor(default_volume=3)
    
    # Simulated price data
    prices = [3500, 3520, 3545, 3530, 3510, 3490, 3470, 3450]
    
    print("\nSimulated trading cycle:")
    for i, price in enumerate(prices):
        broker.set_price("rb0", price)
        
        # Generate simulated signals
        if i == 0:
            signal = "BUY"
        elif i == 3:
            signal = "SELL"
        elif i == 5:
            signal = "SELL"
        elif i == 7:
            signal = "BUY"
        else:
            signal = "HOLD"
        
        print(f"  Day {i+1}: Price={price}, Signal={signal}")
        
        if signal != "HOLD":
            action, volume, _ = signal_processor.process_signal(signal, "rb0")
            
            if "OPEN" in action:
                if action == "BUY_OPEN":
                    broker.buy_open("rb0", volume)
                elif action == "SELL_OPEN":
                    broker.sell_open("rb0", volume)
            elif "CLOSE" in action:
                if action == "CLOSE_LONG":
                    broker.close_long("rb0", volume)
                elif action == "CLOSE_SHORT":
                    broker.close_short("rb0", volume)
    
    print("\nFinal Status:")
    broker.print_status()


def main():
    """Run all demos."""
    print("\n" + "#"*60)
    print("# Paper Broker Demo Suite")
    print("#"*60)
    
    demo_basic_orders()
    demo_signal_processing()
    demo_risk_management()
    demo_multiple_positions()
    demo_with_akshare_prices()
    demo_trading_cycle()
    
    print("\n" + "#"*60)
    print("# All Demos Completed")
    print("#"*60)


if __name__ == "__main__":
    main()
