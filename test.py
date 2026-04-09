import time
from tradingagents.dataflows.akshare_futures import (
    get_main_contract_code,
    get_futures_daily_bars,
    get_futures_basis,
    get_futures_inventory,
    get_futures_historical_indicators,
)

print("Testing akshare futures implementation:")
start_time = time.time()

# Test 1: Get main contract code
print("\n=== Test 1: Get Main Contract Code ===")
result = get_main_contract_code("rb")
print(f"Main contract for 'rb': {result}")

# Test 2: Get daily bars
print("\n=== Test 2: Get Daily Bars ===")
bars = get_futures_daily_bars("rb2410", "2024-05-01", "2024-05-10")
print(f"Daily bars result length: {len(bars)} characters")
print(bars[:500] if len(bars) > 500 else bars)

# Test 3: Get technical indicators
print("\n=== Test 3: Get Technical Indicators (SMA) ===")
indicators = get_futures_historical_indicators("rb2410", "sma", "2024-04-01", "2024-05-10")
print(f"Indicators result length: {len(indicators)} characters")
print(indicators[:500] if len(indicators) > 500 else indicators)

end_time = time.time()
print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
