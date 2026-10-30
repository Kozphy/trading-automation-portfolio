"""Risk manager: position sizing by % risk, daily loss limit, max drawdown guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0      # % of equity risked per trade
    daily_loss_limit_pct: float = 4.0    # prop-firm style daily loss cap
    max_drawdown_pct: float = 10.0       # trailing max drawdown from peak equity
    max_position_notional_pct: float = 100.0  # cap notional as % of equity (leverage cap)


@dataclass
class RiskManager:
    config: RiskConfig = field(default_factory=RiskConfig)
    peak_equity: float = 0.0
    day_start_equity: float = 0.0
    current_day: date | None = None
    halted_reason: str | None = None

    def update_equity(self, equity: float, today: date) -> None:
        if self.current_day != today:
            self.current_day = today
            self.day_start_equity = equity
            if self.halted_reason == "daily_loss":
                self.halted_reason = None  # daily halt resets next day
        self.peak_equity = max(self.peak_equity, equity)
        if self.peak_equity > 0:
            dd = (self.peak_equity - equity) / self.peak_equity * 100
            if dd >= self.config.max_drawdown_pct:
                self.halted_reason = "max_drawdown"  # permanent until manual reset
        if self.day_start_equity > 0 and self.halted_reason != "max_drawdown":
            day_loss = (self.day_start_equity - equity) / self.day_start_equity * 100
            if day_loss >= self.config.daily_loss_limit_pct:
                self.halted_reason = "daily_loss"

    @property
    def can_trade(self) -> bool:
        return self.halted_reason is None

    def position_size(self, equity: float, entry: float, stop: float) -> float:
        """Units to buy/sell so that hitting `stop` loses risk_per_trade_pct of equity."""
        if not self.can_trade:
            return 0.0
        per_unit_risk = abs(entry - stop)
        if per_unit_risk <= 0 or entry <= 0:
            raise ValueError("entry and stop must differ and be positive")
        qty = equity * self.config.risk_per_trade_pct / 100 / per_unit_risk
        max_qty = equity * self.config.max_position_notional_pct / 100 / entry
        return min(qty, max_qty)
