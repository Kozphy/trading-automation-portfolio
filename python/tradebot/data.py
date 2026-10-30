"""OHLCV loading and deterministic SYNTHETIC data generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def generate_synthetic_ohlcv(
    n: int = 2000, seed: int = 42, start_price: float = 30000.0, freq: str = "1h"
) -> pd.DataFrame:
    """Generate SYNTHETIC OHLCV via a regime-switching random walk (deterministic by seed).

    This is not market data; it exists only so tests and demos run offline.
    """
    rng = np.random.default_rng(seed)
    regimes = np.repeat(rng.normal(0, 0.0008, size=n // 200 + 1), 200)[:n]
    rets = regimes + rng.normal(0, 0.006, size=n)
    close = start_price * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[start_price], close[:-1]])
    spread = np.abs(rng.normal(0, 0.003, size=n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.lognormal(mean=3, sigma=0.5, size=n)
    ts = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {"timestamp": ts, "open": open_, "high": high, "low": low, "close": close,
         "volume": volume}
    )


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#")
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)
