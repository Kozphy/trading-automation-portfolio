"""Vectorized backtester with standard performance metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .strategies.base import Strategy


@dataclass
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: dict


def _periods_per_year(ts: pd.Series) -> float:
    delta = ts.diff().median()
    return pd.Timedelta(days=365) / delta if pd.notna(delta) and delta > pd.Timedelta(0) else 252


def compute_metrics(equity: pd.Series, returns: pd.Series, trades: pd.DataFrame,
                    periods_per_year: float) -> dict:
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = len(returns) / periods_per_year
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    dd = equity / equity.cummax() - 1
    std = returns.std()
    sharpe = float(returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0
    pnl = trades["pnl_pct"] if len(trades) else pd.Series(dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_loss = -losses.sum()
    pf = float(wins.sum() / gross_loss) if gross_loss > 0 else float("inf") if len(wins) else 0.0
    return {
        "total_return_pct": float(total_return * 100),
        "cagr_pct": float(cagr * 100),
        "max_drawdown_pct": float(dd.min() * 100),
        "sharpe": sharpe,
        "num_trades": int(len(trades)),
        "win_rate_pct": float(len(wins) / len(pnl) * 100) if len(pnl) else 0.0,
        "profit_factor": pf,
    }


def _extract_trades(df: pd.DataFrame, pos: pd.Series, strat_ret: pd.Series) -> pd.DataFrame:
    rows, start, side = [], None, 0.0
    for i, p in enumerate(pos.to_numpy()):
        if p != side:
            if side != 0 and start is not None:
                r = float(np.prod(1 + strat_ret.iloc[start:i].to_numpy()) - 1)
                rows.append({"entry_time": df["timestamp"].iloc[start],
                             "exit_time": df["timestamp"].iloc[i], "side": side,
                             "pnl_pct": r * 100})
            start, side = (i, p) if p != 0 else (None, 0.0)
    if side != 0 and start is not None:
        r = float(np.prod(1 + strat_ret.iloc[start:].to_numpy()) - 1)
        rows.append({"entry_time": df["timestamp"].iloc[start],
                     "exit_time": df["timestamp"].iloc[-1], "side": side, "pnl_pct": r * 100})
    return pd.DataFrame(rows, columns=["entry_time", "exit_time", "side", "pnl_pct"])


def run_backtest(df: pd.DataFrame, strategy: Strategy, initial_equity: float = 10_000.0,
                 fee_bps: float = 5.0, slippage_bps: float = 2.0) -> BacktestResult:
    """Signals are shifted one bar (execute next bar). Costs charged on position changes."""
    signals = strategy.generate_signals(df).fillna(0.0)
    pos = signals.shift(1).fillna(0.0)
    bar_ret = df["close"].pct_change().fillna(0.0)
    turnover = pos.diff().abs().fillna(pos.abs())
    costs = turnover * (fee_bps + slippage_bps) / 10_000
    strat_ret = pos * bar_ret - costs
    equity = initial_equity * (1 + strat_ret).cumprod()
    equity.index = df["timestamp"]
    trades = _extract_trades(df, pos, strat_ret)
    metrics = compute_metrics(equity, strat_ret, trades, _periods_per_year(df["timestamp"]))
    return BacktestResult(equity, strat_ret, pos, trades, metrics)


def plot_equity(result: BacktestResult, path: str | Path, title: str = "Equity curve") -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(result.equity.index, result.equity.values)
    ax1.set_title(title)
    ax1.set_ylabel("Equity")
    dd = (result.equity / result.equity.cummax() - 1) * 100
    ax2.fill_between(dd.index, dd.values, 0, color="tab:red", alpha=0.4)
    ax2.set_ylabel("Drawdown %")
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path
