import datetime

from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "deepseek-reasoner"  # Use a different model
config["backend_url"] = "https://api.deepseek.com/v1"  # Use a different model
# config["backend_url"] = "https://openrouter.ai/api/v1"  # Use a different model
config["quick_think_llm"] = "deepseek-chat"  # Use a different model
config['llm_provider'] = 'deepseek'  # Change provider to match the new models
config["max_debate_rounds"] = 2  # Increase debate rounds

# Configure data vendors (default uses yfinance, no extra API keys needed)
config["data_vendors"] = {
    "core_stock_apis": "okx",           # Options: , yfinance
    "technical_indicators": "okx",      # Options: , yfinance
    "fundamental_data": "yfinance",          # Options: alpha_vantage, yfinance
    "news_data": "yfinance",                 # Options: alpha_vantage, yfinance
}

# ====== Langfuse 追踪配置（可选）======
# 方式1：代码中配置（需要先 pip install langfuse）
callbacks = [CallbackHandler()]

# Initialize with custom config and optional callbacks
ta = TradingAgentsGraph(debug=True, config=config, callbacks=callbacks)

# forward propagate
_, decision = ta.propagate("ETH-USD", datetime.datetime.now().strftime('%Y-%m-%d'))
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
