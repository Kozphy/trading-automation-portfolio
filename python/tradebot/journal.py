"""Trade-journal analysis: stats + an LLM-ready summary prompt (no API calls made)."""

from __future__ import annotations

import pandas as pd

REQUIRED = {"entry_time", "exit_time", "symbol", "side", "pnl"}


def journal_stats(trades: pd.DataFrame) -> dict:
    missing = REQUIRED - set(trades.columns)
    if missing:
        raise ValueError(f"journal missing columns: {sorted(missing)}")
    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    pnl = t["pnl"]
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    streak = max_streak = 0
    for p in pnl:
        streak = streak + 1 if p <= 0 else 0
        max_streak = max(max_streak, streak)
    hold = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 3600
    t["hour"] = t["entry_time"].dt.hour
    return {
        "num_trades": int(len(t)),
        "net_pnl": float(pnl.sum()),
        "win_rate_pct": float(len(wins) / len(t) * 100) if len(t) else 0.0,
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf"),
        "max_consecutive_losses": int(max_streak),
        "avg_hold_hours": float(hold.mean()) if len(t) else 0.0,
        "pnl_by_symbol": {k: float(v) for k, v in t.groupby("symbol")["pnl"].sum().items()},
        "pnl_by_side": {k: float(v) for k, v in t.groupby("side")["pnl"].sum().items()},
        "pnl_by_entry_hour": {int(k): float(v) for k, v in t.groupby("hour")["pnl"].sum().items()},
    }


def build_llm_prompt(stats: dict, trader_context: str = "") -> str:
    """Return a prompt to paste into any LLM. This function never calls an API."""
    lines = [f"- {k}: {v}" for k, v in stats.items()]
    return (
        "You are a trading-performance coach. Review the journal statistics below and give:\n"
        "1. The three most important behavioural or risk patterns.\n"
        "2. Specific, testable rule changes (e.g. time filters, position sizing).\n"
        "3. What additional data would help.\n"
        "Do not give financial advice or predict prices.\n\n"
        + (f"Trader context: {trader_context}\n\n" if trader_context else "")
        + "Journal statistics:\n" + "\n".join(lines)
    )
