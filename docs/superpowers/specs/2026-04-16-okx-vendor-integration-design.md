# OKX Vendor Integration Design

## Goal
Add `okx` as a new data vendor in `tradingagents/dataflows/interface.py` to replace yfinance for market data (OHLCV + technical indicators) using the existing PostgreSQL database (`market_data.py`). Non-market-data tools (fundamentals, news, etc.) continue to fallback to yfinance.

## Context
- Existing vendors: `yfinance`, `alpha_vantage`
- OKX schema: `KLine` (OHLCV) and `MarketIndicatorHistory` (technical indicators)
- Only symbol currently in DB: `ETH-USDT-SWAP`
- Known data issue: `MarketIndicatorHistory` inserts `1D` records every ~3 minutes, so queries must resample to one record per calendar day.

## Architecture

### New File: `tradingagents/dataflows/okx/client.py`
A thin datastore wrapper around the existing SQLAlchemy engine from `market_data.py`.

```
OKXDataStore
├── engine / session (reuses market_data.py engine)
├── symbol_map: dict[str, str]  # e.g. {"ETH-USD": "ETH-USDT-SWAP"}
├── normalize_symbol(symbol) -> str | None
├── has_symbol(symbol) -> bool
├── get_stock_data(symbol, start_date, end_date) -> str (CSV)
└── get_indicators(symbol, indicator, curr_date, look_back_days) -> str
```

#### `normalize_symbol`
- Maps user-facing tickers (yfinance style) to OKX internal symbols.
- Current map: `{"ETH-USD": "ETH-USDT-SWAP"}`.
- Returns `None` if not mapped.

#### `has_symbol`
- Runs a cheap `SELECT 1 FROM kline WHERE symbol = ? LIMIT 1` to verify the mapped symbol actually exists in the DB.

#### `get_stock_data`
1. Normalize symbol.
2. If not mapped / not in DB → return `"OKX does not have data for {symbol}."`.
3. Query `KLine` where `timeframe = '1D'` and `report_time BETWEEN start_date AND end_date`.
4. Format columns to yfinance-compatible CSV header: `Date,Open,High,Low,Close,Volume`.
5. Return CSV string with header comments.

#### `get_indicators`
1. Normalize symbol.
2. If not mapped / not in DB → return `"OKX does not have data for {symbol}."`.
3. Query `MarketIndicatorHistory` where `timeframe = '1D'` and `DATE(report_time)` in the lookback window.
4. **Resample**: use `DISTINCT ON (DATE(report_time)) ORDER BY report_time DESC` so each calendar day returns the latest record.
5. Map requested indicator name to DB column:
   - `rsi` → `rsi`
   - `macd` → `macd_dif`
   - `macds` → `macd_dea`
   - `macdh` → `macd_hist`
   - `boll` → `bolling_bands->middle`
   - `boll_ub` → `bolling_bands->upper`
   - `boll_lb` → `bolling_bands->lower`
   - `atr` → `atr`
   - `close_10_ema` → `emas->E10` (or fallback)
   - `close_50_sma` → not in DB, fallback message
   - `close_200_sma` → not in DB, fallback message
   - `vwma` → `vmas` 中可用 VMA20/VMA50 近似，fallback 消息也行
6. Format output string exactly like `get_stock_stats_indicators_window`:
   ```
   ## {indicator} values from {before} to {curr_date}:
   {date}: {value}
   ...
   {description}
   ```
7. Indicator descriptions reuse the same dict from `y_finance.py` (or copy a minimal subset into `client.py` to avoid circular imports).

### Modified File: `tradingagents/dataflows/interface.py`
- `VENDOR_LIST += ["okx"]`
- `VENDOR_METHODS` updates:
  - `get_stock_data["okx"] = okx_client.get_okx_stock_data`
  - `get_indicators["okx"] = okx_client.get_okx_indicators`
  - `get_fundamentals["okx"] = yfinance.get_fundamentals`
  - `get_balance_sheet["okx"] = yfinance.get_balance_sheet`
  - `get_cashflow["okx"] = yfinance.get_cashflow`
  - `get_income_statement["okx"] = yfinance.get_income_statement`
  - `get_news["okx"] = yfinance.get_news_yfinance`
  - `get_global_news["okx"] = yfinance.get_global_news_yfinance`
  - `get_insider_transactions["okx"] = yfinance.get_insider_transactions`

### Modified File: `tradingagents/default_config.py` (optional)
Add a comment in `data_vendors` showing `okx` as an available option:
```python
"core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance, okx
```

## Error Handling
- DB connection failure: bubble up as exception (same as existing SQLAlchemy behavior).
- Symbol not in map or DB: return informative string, **not** fallback to yfinance. This matches the user requirement that okx vendor should explicitly report missing data.
- Unsupported indicator for okx: return string saying `"Indicator {indicator} is not available from OKX data."`.

## Testing Checklist
- [ ] `get_okx_stock_data("ETH-USD", "2026-04-01", "2026-04-10")` returns CSV with 10 rows.
- [ ] `get_okx_stock_data("BTC-USD", ...)` returns "OKX does not have data for BTC-USD."
- [ ] `get_okx_indicators("ETH-USD", "rsi", "2026-04-16", 7)` returns one value per day.
- [ ] No `1D` duplicates appear in indicator output (resample works).
- [ ] Interface routing works when `data_vendors["core_stock_apis"] = "okx"`.
