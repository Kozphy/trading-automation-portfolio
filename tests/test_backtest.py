import pandas as pd
import pytest
from tradebot.backtest import plot_equity, run_backtest
from tradebot.strategies import EmaCrossStrategy
from tradebot.strategies.base import Strategy


class AlwaysLong(Strategy):
    def generate_signals(self, df):
        return pd.Series(1.0, index=df.index)


def test_metrics_keys_and_ranges(ohlcv):
    res = run_backtest(ohlcv, EmaCrossStrategy())
    m = res.metrics
    for k in ["cagr_pct", "max_drawdown_pct", "sharpe", "win_rate_pct", "profit_factor"]:
        assert k in m
    assert m["max_drawdown_pct"] <= 0
    assert 0 <= m["win_rate_pct"] <= 100
    assert m["num_trades"] > 0


def test_no_lookahead(ohlcv):
    res = run_backtest(ohlcv, AlwaysLong(), fee_bps=0, slippage_bps=0)
    # first bar has no position, then buy-and-hold from bar 0 close
    expected = ohlcv["close"].iloc[-1] / ohlcv["close"].iloc[0]
    assert res.equity.iloc[-1] / 10_000 == pytest.approx(expected, rel=1e-9)


def test_costs_reduce_returns(ohlcv):
    free = run_backtest(ohlcv, EmaCrossStrategy(), fee_bps=0, slippage_bps=0)
    paid = run_backtest(ohlcv, EmaCrossStrategy(), fee_bps=10, slippage_bps=5)
    assert paid.equity.iloc[-1] < free.equity.iloc[-1]


def test_invalid_params():
    with pytest.raises(ValueError):
        EmaCrossStrategy(50, 20)


def test_plot(tmp_path, ohlcv):
    p = plot_equity(run_backtest(ohlcv, EmaCrossStrategy()), tmp_path / "eq.png")
    assert p.exists() and p.stat().st_size > 1000
