"""Strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """A strategy maps OHLCV bars to a target position series in {-1, 0, 1}.

    Signals at bar t are computed only from data up to and including bar t; the
    backtester shifts them by one bar so trades execute on the next bar (no lookahead).
    """

    name: str = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned with df of target positions (-1 short, 0 flat, 1 long)."""
