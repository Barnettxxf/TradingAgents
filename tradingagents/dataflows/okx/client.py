from typing import Annotated
import datetime
from sqlalchemy import text
from .market_data import engine

SYMBOL_MAP = {
    "ETH-USD": "ETH-USDT-SWAP",
}


def normalize_symbol(symbol: str) -> str | None:
    """Map user-facing ticker to OKX internal symbol."""
    return SYMBOL_MAP.get(symbol.upper())


class OKXDataStore:
    def __init__(self):
        self.engine = engine

    def has_symbol(self, symbol: str) -> bool:
        okx_symbol = normalize_symbol(symbol)
        if not okx_symbol:
            return False
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM kline WHERE symbol = :sym LIMIT 1"),
                {"sym": okx_symbol},
            )
            return result.fetchone() is not None
