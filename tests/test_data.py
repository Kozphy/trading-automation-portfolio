from tradebot.data import generate_synthetic_ohlcv


def test_synthetic_is_deterministic():
    a, b = generate_synthetic_ohlcv(500, seed=1), generate_synthetic_ohlcv(500, seed=1)
    assert a.equals(b)


def test_ohlc_consistency(ohlcv):
    assert (ohlcv["high"] >= ohlcv[["open", "close"]].max(axis=1)).all()
    assert (ohlcv["low"] <= ohlcv[["open", "close"]].min(axis=1)).all()
    assert len(ohlcv) == 3000
