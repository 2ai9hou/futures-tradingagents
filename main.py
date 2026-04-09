from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-5.4-mini"
config["quick_think_llm"] = "gpt-5.4-mini"
config["max_debate_rounds"] = 1

# Configure data vendors for Chinese Futures Market (akshare)
config["data_vendors"] = {
    "core_stock_apis": "akshare",
    "technical_indicators": "akshare",
    "fundamental_data": "akshare",
    "news_data": "akshare",
}

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate with futures symbol
# Example: 'rb' for rebar futures, 'hc' for hot rolled coil, 'i' for iron ore
_, decision = ta.propagate("rb", "2024-05-10")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
