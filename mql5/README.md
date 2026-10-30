# MQL5 Expert Advisor

> **Status: uncompiled.** This code was written without access to MetaEditor. Compile it and fix any warnings before you rely on it. Run it on a **demo account** only.

## Files
- `RangeBreakoutEA.mq5`: session range breakout EA
  - Builds the high/low range between `InpRangeStartHour` and `InpRangeEndHour` (broker server time) and enters on a breakout plus a buffer.
  - **Lot sizing by % risk:** lots = (equity × risk%) / (stop distance in ticks × tick value). The trade is skipped if the size is below the broker minimum.
  - The stop goes on the opposite side of the range. The optional final TP is set at N × R.
  - **Partial take-profit:** closes X% at `InpPartialAtR` R, then moves the stop to breakeven.
  - **ATR trailing stop:** only ever tightens.
  - **Prop-firm guards:** a daily loss limit (measured against the day-start balance) and a max drawdown from peak equity. Either one can flatten positions.
  - Optional ZigZag/Fibonacci swing filter.
- `Include/SwingFib.mqh`: ZigZag-style alternating swing detection (confirmed swings only, no repainting), `FibLevel()` and `InFibZone()`.

## Compile
1. In MT5, go to **File → Open Data Folder** and copy `RangeBreakoutEA.mq5` to `MQL5/Experts/` and `Include/SwingFib.mqh` to `MQL5/Experts/Include/`. The EA includes `"Include\SwingFib.mqh"` relative to itself. If you'd rather put it in `MQL5/Include/`, change the include to `<SwingFib.mqh>`.
2. Open the EA in MetaEditor and press **F7 (Compile)**.

## Backtest in Strategy Tester
1. Press **Ctrl+R** in MT5 and select `RangeBreakoutEA`.
2. Pick a symbol (for example XAUUSD or EURUSD) and a timeframe of M15 or H1.
3. Set Modelling to **"Every tick based on real ticks"** for realistic fills.
4. Set the deposit and leverage to match your prop-firm challenge, then set `InpDailyLossPct` and `InpMaxDrawdownPct` to the firm's rules.
5. Run it and check the report's drawdown, profit factor and trade count. Use **Optimization** on the session hours and ATR multiple, then validate on out-of-sample dates.

Session hours use broker **server time**, so adjust them for your broker's GMT offset.
