import datetime
from typing import Annotated

from sqlalchemy import text
from .market_data import engine as _default_engine

SYMBOL_MAP = {
    "ETH-USD": "ETH-USDT-SWAP",
}


def normalize_symbol(symbol: str) -> str | None:
    """Map user-facing ticker to OKX internal symbol."""
    return SYMBOL_MAP.get(symbol.upper())


class OKXDataStore:
    """Thin wrapper around the OKX PostgreSQL datastore."""

    def __init__(self, engine=None):
        self.engine = engine if engine is not None else _default_engine

    def has_symbol(self, symbol: str) -> bool:
        """Return True if the normalized symbol exists in the kline table."""
        okx_symbol = normalize_symbol(symbol)
        if not okx_symbol:
            return False
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM kline WHERE symbol = :sym LIMIT 1"),
                {"sym": okx_symbol},
            )
            return result.fetchone() is not None


def get_okx_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):
    datetime.datetime.strptime(start_date, "%Y-%m-%d")
    datetime.datetime.strptime(end_date, "%Y-%m-%d")

    okx_symbol = normalize_symbol(symbol)
    if not okx_symbol:
        return f"OKX does not have data for {symbol}."

    store = OKXDataStore()
    if not store.has_symbol(symbol):
        return f"OKX does not have data for {symbol}."

    with store.engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT report_time, open, high, low, close, vol
                FROM kline
                WHERE symbol = :sym
                  AND timeframe = '1D'
                  AND report_time BETWEEN :start AND :end
                ORDER BY report_time
            """),
            {"sym": okx_symbol, "start": start_date, "end": end_date},
        )
        rows = result.fetchall()

    if not rows:
        return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

    lines = ["Date,Open,High,Low,Close,Adj Close,Volume"]
    for row in rows:
        lines.append(
            f"{row.report_time.strftime('%Y-%m-%d')},"
            f"{round(row.open, 2) if row.open is not None else ''},"
            f"{round(row.high, 2) if row.high is not None else ''},"
            f"{round(row.low, 2) if row.low is not None else ''},"
            f"{round(row.close, 2) if row.close is not None else ''},"
            f"{round(row.close, 2) if row.close is not None else ''},"
            f"{round(row.vol, 2) if row.vol is not None else ''}"
        )

    csv_body = "\n".join(lines)
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(rows)}\n"
    header += f"# Data retrieved on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    return header + csv_body


_INDICATOR_DESCS = {
    "close_50_sma": (
        "50 SMA: A medium-term trend indicator. "
        "Usage: Identify trend direction and serve as dynamic support/resistance. "
        "Tips: It lags price; combine with faster indicators for timely signals."
    ),
    "close_200_sma": (
        "200 SMA: A long-term trend benchmark. "
        "Usage: Confirm overall market trend and identify golden/death cross setups. "
        "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
    ),
    "close_10_ema": (
        "10 EMA: A responsive short-term average. "
        "Usage: Capture quick shifts in momentum and potential entry points. "
        "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
    ),
    "macd": (
        "MACD: Computes momentum via differences of EMAs. "
        "Usage: Look for crossovers and divergence as signals of trend changes. "
        "Tips: Confirm with other indicators in low-volatility or sideways markets."
    ),
    "macds": (
        "MACD Signal: An EMA smoothing of the MACD line. "
        "Usage: Use crossovers with the MACD line to trigger trades. "
        "Tips: Should be part of a broader strategy to avoid false positives."
    ),
    "macdh": (
        "MACD Histogram: Shows the gap between the MACD line and its signal. "
        "Usage: Visualize momentum strength and spot divergence early. "
        "Tips: Can be volatile; complement with additional filters in fast-moving markets."
    ),
    "rsi": (
        "RSI: Measures momentum to flag overbought/oversold conditions. "
        "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
        "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
    ),
    "boll": (
        "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
        "Usage: Acts as a dynamic benchmark for price movement. "
        "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
    ),
    "boll_ub": (
        "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
        "Usage: Signals potential overbought conditions and breakout zones. "
        "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
    ),
    "boll_lb": (
        "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
        "Usage: Indicates potential oversold conditions. "
        "Tips: Use additional analysis to avoid false reversal signals."
    ),
    "atr": (
        "ATR: Averages true range to measure volatility. "
        "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
        "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
    ),
    "vwma": (
        "VWMA: A moving average weighted by volume. "
        "Usage: Confirm trends by integrating price action with volume data. "
        "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
    ),
}

_INDICATOR_COLUMN_MAP = {
    "rsi": "rsi",
    "macd": "macd_dif",
    "macds": "macd_dea",
    "macdh": "macd_hist",
    "atr": "atr",
}


def _extract_indicator_value(row, indicator: str):
    """Extract a scalar value from a result row for the requested indicator."""
    if indicator in _INDICATOR_COLUMN_MAP:
        col = _INDICATOR_COLUMN_MAP[indicator]
        val = getattr(row, col)
        if val is None:
            return "N/A"
        return str(val)

    if indicator == "boll":
        bb = row.bolling_bands or {}
        val = bb.get("middle")
        return str(val) if val is not None else "N/A"
    if indicator == "boll_ub":
        bb = row.bolling_bands or {}
        val = bb.get("upper")
        return str(val) if val is not None else "N/A"
    if indicator == "boll_lb":
        bb = row.bolling_bands or {}
        val = bb.get("lower")
        return str(val) if val is not None else "N/A"
    if indicator == "close_10_ema":
        emas = row.emas or {}
        val = emas.get("E10")
        if val is None:
            val = emas.get("E5")
        return str(val) if val is not None else "N/A"

    return None


def get_okx_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    okx_symbol = normalize_symbol(symbol)
    if not okx_symbol:
        return f"OKX does not have data for {symbol}."

    if indicator not in _INDICATOR_DESCS:
        return (
            f"Indicator {indicator} is not supported. Please choose from: "
            f"{list(_INDICATOR_DESCS.keys())}"
        )

    curr_date_dt = datetime.datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - datetime.timedelta(days=look_back_days)

    store = OKXDataStore()
    if not store.has_symbol(symbol):
        return f"OKX does not have data for {symbol}."

    with store.engine.connect() as conn:
        # DISTINCT ON is required because multiple indicator calculations may
        # exist per calendar day; we want the latest one for each day.
        result = conn.execute(
            text("""
                SELECT DISTINCT ON (DATE(report_time))
                    report_time,
                    rsi,
                    macd_dif,
                    macd_dea,
                    macd_hist,
                    atr,
                    bolling_bands,  -- matches the DB schema spelling
                    emas
                FROM market_indicator_history
                WHERE symbol = :sym
                  AND timeframe = '1D'
                  AND report_time >= :start
                  AND report_time < :end_plus_one
                ORDER BY DATE(report_time), report_time DESC
            """),
            {
                "sym": okx_symbol,
                "start": before.strftime("%Y-%m-%d"),
                "end_plus_one": (curr_date_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            },
        )
        rows = result.fetchall()

    rows_by_date = {r.report_time.strftime("%Y-%m-%d"): r for r in rows}

    # Build daily index from before..curr_date inclusive
    ind_string = ""
    current_dt = curr_date_dt
    while current_dt >= before:
        date_str = current_dt.strftime("%Y-%m-%d")
        row_for_date = rows_by_date.get(date_str)

        if row_for_date:
            val = _extract_indicator_value(row_for_date, indicator)
            if val is None:
                val = f"N/A: Indicator {indicator} is not available from OKX data."
        else:
            val = "N/A: Not a trading day (weekend or holiday)"

        ind_string += f"{date_str}: {val}\n"
        current_dt -= datetime.timedelta(days=1)

    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + ind_string
        + "\n\n"
        + _INDICATOR_DESCS.get(indicator, "No description available.")
    )
    return result_str
