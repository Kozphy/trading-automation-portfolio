"""Run the example strategy on bundled synthetic data; print metrics and save equity PNG."""

import argparse
import json
from pathlib import Path

from tradebot.backtest import plot_equity, run_backtest
from tradebot.data import load_ohlcv
from tradebot.strategies import EmaCrossStrategy

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_btcusdt_1h.csv"))
    ap.add_argument("--fast", type=int, default=20)
    ap.add_argument("--slow", type=int, default=50)
    ap.add_argument("--out", default=str(ROOT / "docs" / "equity_curve.png"))
    a = ap.parse_args()
    df = load_ohlcv(a.data)
    res = run_backtest(df, EmaCrossStrategy(a.fast, a.slow))
    plot_equity(res, a.out, title=f"EMA {a.fast}/{a.slow} on SYNTHETIC data")
    print(json.dumps({k: round(v, 3) for k, v in res.metrics.items()}, indent=2))
    print(f"equity curve -> {a.out}")
