from pathlib import Path

import pytest
from tradebot.data import load_ohlcv

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def ohlcv():
    return load_ohlcv(DATA / "synthetic_btcusdt_1h.csv")


@pytest.fixture
def journal_path():
    return DATA / "synthetic_trade_journal.csv"
