from fastapi.testclient import TestClient
from tradebot.connectors import PaperExecutor
from tradebot.webhook import create_app


def client():
    return TestClient(create_app(PaperExecutor(fee_bps=0), secret="s3cret"))


def test_health():
    assert client().get("/health").json()["mode"] == "paper"


def test_valid_alert_fills():
    r = client().post("/webhook/tradingview", json={
        "secret": "s3cret", "symbol": "BTC/USDT", "side": "buy", "qty": 0.01, "price": 60000})
    assert r.status_code == 200
    assert r.json()["position"] == 0.01


def test_bad_secret_rejected():
    r = client().post("/webhook/tradingview", json={
        "secret": "nope", "symbol": "BTC/USDT", "side": "buy", "qty": 1, "price": 1})
    assert r.status_code == 401


def test_invalid_payload():
    r = client().post("/webhook/tradingview", json={
        "secret": "s3cret", "symbol": "BTC/USDT", "side": "hold", "qty": 1, "price": 1})
    assert r.status_code == 422
