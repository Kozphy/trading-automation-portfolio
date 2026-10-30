from datetime import date

import pytest
from tradebot.risk import RiskConfig, RiskManager


def test_position_size_risk_pct():
    rm = RiskManager(RiskConfig(risk_per_trade_pct=1.0, max_position_notional_pct=1000))
    qty = rm.position_size(10_000, entry=100, stop=98)
    assert qty * 2 == pytest.approx(100)  # loses 1% of 10k at stop


def test_notional_cap():
    rm = RiskManager(RiskConfig(risk_per_trade_pct=5, max_position_notional_pct=100))
    assert rm.position_size(10_000, 100, 99.9) == pytest.approx(100)


def test_daily_loss_halts_and_resets():
    rm = RiskManager(RiskConfig(daily_loss_limit_pct=4, max_drawdown_pct=50))
    rm.update_equity(10_000, date(2024, 1, 1))
    rm.update_equity(9_500, date(2024, 1, 1))
    assert rm.halted_reason == "daily_loss" and rm.position_size(9_500, 100, 99) == 0
    rm.update_equity(9_500, date(2024, 1, 2))
    assert rm.can_trade


def test_max_drawdown_is_permanent():
    rm = RiskManager(RiskConfig(daily_loss_limit_pct=50, max_drawdown_pct=10))
    rm.update_equity(10_000, date(2024, 1, 1))
    rm.update_equity(8_900, date(2024, 1, 2))
    rm.update_equity(9_000, date(2024, 1, 3))
    assert rm.halted_reason == "max_drawdown"


def test_bad_stop():
    with pytest.raises(ValueError):
        RiskManager().position_size(1000, 100, 100)
