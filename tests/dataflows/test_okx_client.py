import pytest
from tradingagents.dataflows.okx.client import (
    normalize_symbol,
    get_okx_stock_data,
    get_okx_indicators,
)


def test_normalize_symbol_maps_eth_usd():
    assert normalize_symbol("ETH-USD") == "ETH-USDT-SWAP"
    assert normalize_symbol("eth-usd") == "ETH-USDT-SWAP"


def test_normalize_symbol_returns_none_for_unknown():
    assert normalize_symbol("BTC-USD") is None
    assert normalize_symbol("AAPL") is None


def test_get_okx_stock_data_unknown_symbol():
    result = get_okx_stock_data("BTC-USD", "2026-04-10", "2026-04-12")
    assert "OKX does not have data for BTC-USD" in result


def test_get_okx_stock_data_eth_returns_csv():
    result = get_okx_stock_data("ETH-USD", "2026-04-10", "2026-04-12")
    assert "Stock data for ETH-USD" in result
    assert "Total records:" in result
    assert "Date,Open,High,Low,Close,Adj Close,Volume" in result


def test_get_okx_indicators_unknown_symbol():
    result = get_okx_indicators("BTC-USD", "rsi", "2026-04-16", 3)
    assert "OKX does not have data for BTC-USD" in result


def test_get_okx_indicators_rsi_format():
    result = get_okx_indicators("ETH-USD", "rsi", "2026-04-16", 3)
    assert "rsi values" in result.lower()
    assert "2026-04-16" in result
    assert "RSI: Measures momentum" in result


def test_get_okx_indicators_no_duplicate_days():
    result = get_okx_indicators("ETH-USD", "macd", "2026-04-16", 7)
    dates = []
    for line in result.splitlines():
        if line.startswith("2026-"):
            date_part = line.split(":")[0]
            dates.append(date_part)
    assert len(dates) == len(set(dates))


def test_get_okx_indicators_sma_computed_from_kline():
    result = get_okx_indicators("ETH-USD", "close_50_sma", "2026-04-16", 3)
    assert "close_50_sma values" in result.lower()
    assert "2026-04-16" in result
    # Values should be numeric, not N/A
    for line in result.splitlines():
        if line.startswith("2026-"):
            value = line.split(":")[1].strip()
            assert value != "N/A"
            assert float(value) > 0
