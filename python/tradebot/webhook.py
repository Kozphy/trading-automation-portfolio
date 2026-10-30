"""FastAPI TradingView webhook receiver -> PaperExecutor.

TradingView alert message (JSON) example:
  {"secret": "...", "symbol": "BTC/USDT", "side": "buy", "qty": 0.01, "price": 65000}
Secret is read from env TRADEBOT_WEBHOOK_SECRET. Run:
  uvicorn tradebot.webhook:app --port 8000
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .connectors.paper import PaperExecutor


class TVAlert(BaseModel):
    secret: str
    symbol: str
    side: str = Field(pattern="^(buy|sell|BUY|SELL)$")
    qty: float = Field(gt=0)
    price: float = Field(gt=0)


def create_app(executor: PaperExecutor | None = None, secret: str | None = None) -> FastAPI:
    app = FastAPI(title="tradebot TradingView webhook (paper)")
    app.state.executor = executor or PaperExecutor()
    expected = secret if secret is not None else os.getenv("TRADEBOT_WEBHOOK_SECRET", "")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "mode": "paper"}

    @app.post("/webhook/tradingview")
    def tradingview(alert: TVAlert) -> dict:
        if not expected or not hmac.compare_digest(alert.secret, expected):
            raise HTTPException(status_code=401, detail="invalid secret")
        ex: PaperExecutor = app.state.executor
        try:
            order = ex.place_order(alert.symbol, alert.side, alert.qty, alert.price)
        except PermissionError as e:
            raise HTTPException(status_code=423, detail=str(e)) from e
        return {"status": "filled", "symbol": order.symbol, "side": order.side,
                "qty": order.qty, "price": order.price,
                "position": ex.positions[order.symbol], "equity": ex.equity()}

    return app


app = create_app()
