"""ccxt connector layer for Binance / Bybit / OKX.

Safety defaults:
* mode defaults to "paper" (no exchange object with keys is created).
* "testnet" uses the exchange sandbox; "live" requires TRADEBOT_ALLOW_LIVE=1.
* API keys are read ONLY from environment variables, never from code or config files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SUPPORTED_EXCHANGES = {"binance", "bybit", "okx"}
MODES = {"paper", "testnet", "live"}


@dataclass
class ExchangeConfig:
    exchange_id: str = "binance"
    mode: str = "paper"

    def __post_init__(self) -> None:
        self.exchange_id = self.exchange_id.lower()
        if self.exchange_id not in SUPPORTED_EXCHANGES:
            raise ValueError(f"unsupported exchange {self.exchange_id!r}")
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {sorted(MODES)}")

    def credentials(self) -> dict:
        """Read keys from env: e.g. BINANCE_API_KEY, BINANCE_API_SECRET, OKX_API_PASSWORD."""
        p = self.exchange_id.upper()
        creds = {"apiKey": os.getenv(f"{p}_API_KEY"), "secret": os.getenv(f"{p}_API_SECRET")}
        if self.exchange_id == "okx":
            creds["password"] = os.getenv("OKX_API_PASSWORD")
        return {k: v for k, v in creds.items() if v}


def create_exchange(config: ExchangeConfig):
    """Return a configured ccxt exchange. In paper mode returns a key-less public client
    (market data only); order placement should go through PaperExecutor."""
    try:
        import ccxt  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install 'tradebot[exchange]' to use ccxt connectors") from e

    klass = getattr(ccxt, config.exchange_id)
    params: dict = {"enableRateLimit": True}
    if config.mode == "live" and os.getenv("TRADEBOT_ALLOW_LIVE") != "1":
        raise PermissionError("live trading disabled; set TRADEBOT_ALLOW_LIVE=1 to opt in")
    if config.mode in {"testnet", "live"}:
        params.update(config.credentials())
    ex = klass(params)
    if config.mode == "testnet":
        ex.set_sandbox_mode(True)
    return ex


def fetch_ohlcv_df(exchange, symbol: str, timeframe: str = "1h", limit: int = 500):
    """Fetch OHLCV into a DataFrame compatible with tradebot.backtest (network call)."""
    import pandas as pd

    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df
