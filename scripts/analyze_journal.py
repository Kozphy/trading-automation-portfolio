"""Print journal stats and the LLM-ready prompt for the bundled synthetic journal."""

from pathlib import Path

import pandas as pd
from tradebot.journal import build_llm_prompt, journal_stats

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    df = pd.read_csv(ROOT / "data" / "synthetic_trade_journal.csv", comment="#")
    print(build_llm_prompt(journal_stats(df), "Synthetic demo journal"))
