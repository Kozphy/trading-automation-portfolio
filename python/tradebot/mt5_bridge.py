"""Optional MetaTrader 5 bridge (Windows + MT5 terminal + `pip install MetaTrader5`).

The import is guarded so the rest of the package works on Linux/macOS/CI.
"""

from __future__ import annotations

try:  # pragma: no cover - depends on platform
    import MetaTrader5 as mt5  # type: ignore

    MT5_AVAILABLE = True
except ImportError:  # pragma: no cover
    mt5 = None
    MT5_AVAILABLE = False


class MT5Unavailable(RuntimeError):
    pass


def _require() -> None:
    if not MT5_AVAILABLE:
        raise MT5Unavailable("MetaTrader5 package not installed (Windows only)")


def connect(login: int | None = None, password: str | None = None,
            server: str | None = None) -> bool:  # pragma: no cover
    _require()
    kwargs = {k: v for k, v in {"login": login, "password": password, "server": server}.items()
              if v is not None}
    return bool(mt5.initialize(**kwargs))


def fetch_rates(symbol: str, timeframe: str = "H1", count: int = 500):  # pragma: no cover
    _require()
    import pandas as pd

    tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.rename(columns={"tick_volume": "volume"})[
        ["timestamp", "open", "high", "low", "close", "volume"]]


def market_order(symbol: str, side: str, volume: float, sl: float = 0.0, tp: float = 0.0,
                 magic: int = 20260101, deviation: int = 20):  # pragma: no cover
    """Send a market order. Use a DEMO account first."""
    _require()
    tick = mt5.symbol_info_tick(symbol)
    is_buy = side.lower() == "buy"
    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": tick.ask if is_buy else tick.bid, "sl": sl, "tp": tp,
        "deviation": deviation, "magic": magic, "comment": "tradebot",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)
