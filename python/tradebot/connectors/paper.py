"""In-memory paper executor: simulated fills, positions, PnL, risk checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..risk import RiskManager


@dataclass
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    price: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fee: float = 0.0


@dataclass
class PaperExecutor:
    cash: float = 10_000.0
    fee_bps: float = 5.0
    risk: RiskManager = field(default_factory=RiskManager)
    positions: dict[str, float] = field(default_factory=dict)
    avg_price: dict[str, float] = field(default_factory=dict)
    last_price: dict[str, float] = field(default_factory=dict)
    orders: list[Order] = field(default_factory=list)
    realized_pnl: float = 0.0

    def equity(self) -> float:
        return self.cash + sum(q * self.last_price.get(s, 0.0) for s, q in self.positions.items())

    def place_order(self, symbol: str, side: str, qty: float, price: float) -> Order:
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")
        self.last_price[symbol] = price
        self.risk.update_equity(self.equity(), datetime.now(timezone.utc).date())
        cur = self.positions.get(symbol, 0.0)
        signed = qty if side == "buy" else -qty
        reduces = cur != 0 and (cur > 0) != (signed > 0)
        if not self.risk.can_trade and not reduces:
            raise PermissionError(f"risk halt: {self.risk.halted_reason}")
        fee = qty * price * self.fee_bps / 10_000
        new = cur + signed
        if reduces:
            closed = min(abs(signed), abs(cur))
            self.realized_pnl += closed * (price - self.avg_price[symbol]) * (1 if cur > 0 else -1)
        if new == 0:
            self.avg_price.pop(symbol, None)
        elif cur == 0 or (cur > 0) != (new > 0):
            self.avg_price[symbol] = price
        elif not reduces:
            self.avg_price[symbol] = (self.avg_price[symbol] * abs(cur) + price * qty) / abs(new)
        self.positions[symbol] = new
        self.cash -= signed * price + fee
        self.realized_pnl -= fee
        order = Order(symbol, side, qty, price, fee=fee)
        self.orders.append(order)
        return order
