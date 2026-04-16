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
