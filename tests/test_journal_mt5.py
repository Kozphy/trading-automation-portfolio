import pandas as pd
import pytest
from tradebot import mt5_bridge
from tradebot.journal import build_llm_prompt, journal_stats


def test_journal_stats(journal_path):
    s = journal_stats(pd.read_csv(journal_path, comment="#"))
    assert s["num_trades"] == 60
    assert 0 <= s["win_rate_pct"] <= 100
    assert set(s["pnl_by_side"]) <= {"long", "short"}


def test_prompt_contains_stats(journal_path):
    s = journal_stats(pd.read_csv(journal_path, comment="#"))
    p = build_llm_prompt(s, "demo")
    assert "win_rate_pct" in p and "financial advice" in p


def test_missing_columns():
    with pytest.raises(ValueError):
        journal_stats(pd.DataFrame({"pnl": [1]}))


def test_mt5_guarded():
    if not mt5_bridge.MT5_AVAILABLE:
        with pytest.raises(mt5_bridge.MT5Unavailable):
            mt5_bridge.connect()
