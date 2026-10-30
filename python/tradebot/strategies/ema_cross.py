"""Example strategy: EMA crossover with ATR volatility filter."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


class EmaCrossStrategy(Strategy):
    name = "ema_cross"

    def __init__(self, fast: int = 20, slow: int = 50, allow_short: bool = False,
                 min_atr_pct: float = 0.0):
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self.fast, self.slow = fast, slow
        self.allow_short = allow_short
        self.min_atr_pct = min_atr_pct

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        sig = np.where(fast > slow, 1, -1 if self.allow_short else 0)
        sig = pd.Series(sig, index=df.index, dtype=float)
        sig.iloc[: self.slow] = 0.0  # warm-up
        if self.min_atr_pct > 0:
            vol_ok = (atr(df) / df["close"]).fillna(0) >= self.min_atr_pct
            sig = sig.where(vol_ok, 0.0)
        return sig
