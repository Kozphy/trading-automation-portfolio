import pytest
from tradebot.connectors import ExchangeConfig, PaperExecutor, create_exchange


def test_unsupported_exchange():
    with pytest.raises(ValueError):
        ExchangeConfig("kraken")


def test_credentials_from_env(monkeypatch):
    monkeypatch.setenv("OKX_API_KEY", "k")
    monkeypatch.setenv("OKX_API_SECRET", "s")
    monkeypatch.setenv("OKX_API_PASSWORD", "p")
    assert ExchangeConfig("okx").credentials() == {"apiKey": "k", "secret": "s", "password": "p"}


def test_paper_default_has_no_keys(monkeypatch):
    pytest.importorskip("ccxt")
    monkeypatch.setenv("BINANCE_API_KEY", "should-not-be-used")
    ex = create_exchange(ExchangeConfig("binance"))
    assert not ex.apiKey


def test_live_requires_opt_in(monkeypatch):
    pytest.importorskip("ccxt")
    monkeypatch.delenv("TRADEBOT_ALLOW_LIVE", raising=False)
    with pytest.raises(PermissionError):
        create_exchange(ExchangeConfig("bybit", mode="live"))


def test_paper_round_trip():
    ex = PaperExecutor(cash=10_000, fee_bps=0)
    ex.place_order("BTC/USDT", "buy", 0.1, 50_000)
    ex.place_order("BTC/USDT", "sell", 0.1, 51_000)
    assert ex.positions["BTC/USDT"] == 0
    assert ex.realized_pnl == pytest.approx(100)
    assert ex.cash == pytest.approx(10_100)


def test_paper_rejects_bad_side():
    with pytest.raises(ValueError):
        PaperExecutor().place_order("X", "hold", 1, 1)
