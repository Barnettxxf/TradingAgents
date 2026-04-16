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
