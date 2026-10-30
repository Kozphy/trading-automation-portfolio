//+------------------------------------------------------------------+
//| RangeBreakoutEA.mq5                                              |
//| Session/range breakout EA with prop-firm style risk controls.    |
//|  - Builds a high/low range during a configurable session window  |
//|  - Enters on breakout of the range after the window closes       |
//|  - Lot size from % account risk and stop distance                |
//|  - ATR trailing stop, partial take-profit at R multiple          |
//|  - Daily loss limit and max equity drawdown guard                |
//|  - Optional Fibonacci/ZigZag swing confirmation filter           |
//| EDUCATIONAL CODE - NOT FINANCIAL ADVICE. Test on demo only.      |
//| Written without a compiler: compile & verify in MetaEditor.      |
//+------------------------------------------------------------------+
#property copyright "Kozphy - trading-automation-portfolio"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include "Include\SwingFib.mqh"

//--- Inputs: range/session
input group "Session range"
input int    InpRangeStartHour   = 0;     // Range start hour (server time)
input int    InpRangeEndHour     = 7;     // Range end hour (exclusive)
input int    InpTradeEndHour     = 20;    // No new entries after this hour
input int    InpBreakoutBufferPts= 20;    // Buffer above/below range in points
input bool   InpOneTradePerDay   = true;  // Only one breakout trade per day

input group "Risk"
input double InpRiskPercent      = 0.5;   // Risk per trade, % of equity
input double InpDailyLossPct     = 4.0;   // Daily loss limit, % of day-start balance
input double InpMaxDrawdownPct   = 8.0;   // Max drawdown from peak equity, %
input bool   InpCloseOnLimit     = true;  // Close positions when a limit is hit

input group "Exits"
input int    InpAtrPeriod        = 14;    // ATR period
input double InpAtrTrailMult     = 2.0;   // ATR trailing multiple
input double InpPartialAtR       = 1.0;   // Partial TP when profit reaches this R
input double InpPartialPercent   = 50.0;  // % of volume to close at partial TP
input double InpFinalTpR         = 3.0;   // Final TP in R (0 = none, trail only)

input group "Filters"
input bool   InpUseFibFilter     = false; // Require breakout direction = last swing leg
input int    InpSwingDepth       = 5;     // Swing depth (bars each side)
input int    InpSwingLookback    = 200;   // Bars to search for swings

input group "Misc"
input ulong  InpMagic            = 20260101;
input int    InpSlippagePts      = 20;

//--- Globals
CTrade   trade;
int      atrHandle   = INVALID_HANDLE;
double   peakEquity  = 0.0;
double   dayStartBal = 0.0;
int      currentDay  = -1;
bool     tradedToday = false;
bool     ddHalted    = false;   // permanent until EA restart (prop-firm style)
bool     dayHalted   = false;
double   rangeHigh   = 0.0, rangeLow = 0.0;
bool     rangeReady  = false;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpRangeEndHour <= InpRangeStartHour || InpTradeEndHour <= InpRangeEndHour)
     {
      Print("Invalid session hours");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)
     {
      Print("Risk percent must be in (0, 5]");
      return INIT_PARAMETERS_INCORRECT;
     }
   atrHandle = iATR(_Symbol, _Period, InpAtrPeriod);
   if(atrHandle == INVALID_HANDLE)
     {
      Print("Failed to create ATR handle: ", GetLastError());
      return INIT_FAILED;
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePts);
   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(atrHandle != INVALID_HANDLE) IndicatorRelease(atrHandle);
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
double GetATR()
  {
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(atrHandle, 0, 1, 1, buf) != 1) return 0.0; // last closed bar
   return buf[0];
  }

int ServerHour()
  {
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   return t.hour;
  }

int ServerDayOfYear()
  {
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   return t.day_of_year;
  }

double NormalizeLots(double lots)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   if(lots < minL) return 0.0;           // too small to respect risk -> skip trade
   return MathMin(lots, maxL);
  }

//--- Lots such that a stop of `stopDist` price units loses InpRiskPercent of equity.
double LotsForRisk(double stopDist)
  {
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0 || stopDist <= 0) return 0.0;
   double riskMoney   = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
   double lossPerLot  = stopDist / tickSize * tickValue;
   return NormalizeLots(riskMoney / lossPerLot);
  }

int CountMyPositions()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == (long)InpMagic) n++;
     }
   return n;
  }

void CloseAllMine()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
         trade.PositionClose(ticket);
     }
  }

//+------------------------------------------------------------------+
//| Risk guards: daily loss + max drawdown                           |
//+------------------------------------------------------------------+
bool RiskGuardsOk()
  {
   int doy = ServerDayOfYear();
   if(doy != currentDay)
     {
      currentDay  = doy;
      dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
      dayHalted   = false;
      tradedToday = false;
      rangeReady  = false;
     }
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > peakEquity) peakEquity = equity;

   if(!ddHalted && peakEquity > 0 &&
      (peakEquity - equity) / peakEquity * 100.0 >= InpMaxDrawdownPct)
     {
      ddHalted = true;
      PrintFormat("Max drawdown %.2f%% hit - trading halted", InpMaxDrawdownPct);
      if(InpCloseOnLimit) CloseAllMine();
     }
   if(!dayHalted && dayStartBal > 0 &&
      (dayStartBal - equity) / dayStartBal * 100.0 >= InpDailyLossPct)
     {
      dayHalted = true;
      PrintFormat("Daily loss limit %.2f%% hit - halted until next day", InpDailyLossPct);
      if(InpCloseOnLimit) CloseAllMine();
     }
   return !ddHalted && !dayHalted;
  }

//+------------------------------------------------------------------+
//| Range building: high/low of bars inside [start, end) today        |
//+------------------------------------------------------------------+
void BuildRange()
  {
   if(rangeReady || ServerHour() < InpRangeEndHour) return;
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   t.hour = InpRangeStartHour; t.min = 0; t.sec = 0;
   datetime from = StructToTime(t);
   t.hour = InpRangeEndHour;
   datetime to = StructToTime(t) - 1;
   MqlRates rates[];
   int n = CopyRates(_Symbol, _Period, from, to, rates);
   if(n <= 0) return;
   rangeHigh = rates[0].high; rangeLow = rates[0].low;
   for(int i = 1; i < n; i++)
     {
      rangeHigh = MathMax(rangeHigh, rates[i].high);
      rangeLow  = MathMin(rangeLow,  rates[i].low);
     }
   rangeReady = true;
   PrintFormat("Range built: high=%.5f low=%.5f bars=%d", rangeHigh, rangeLow, n);
  }

//--- Optional swing filter: last confirmed leg must agree with breakout direction.
bool SwingFilterOk(bool isBuy)
  {
   if(!InpUseFibFilter) return true;
   SwingPoint sw[];
   if(FindSwings(_Symbol, _Period, InpSwingDepth, InpSwingLookback, sw, 2) < 2) return false;
   // sw[0] = newest swing. Up leg if newest is a high.
   bool upLeg = sw[0].isHigh;
   return isBuy ? upLeg : !upLeg;
  }

//+------------------------------------------------------------------+
//| Entry                                                             |
//+------------------------------------------------------------------+
void CheckEntry()
  {
   if(!rangeReady || CountMyPositions() > 0) return;
   if(InpOneTradePerDay && tradedToday) return;
   int h = ServerHour();
   if(h < InpRangeEndHour || h >= InpTradeEndHour) return;

   double buffer = InpBreakoutBufferPts * _Point;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   bool buySignal  = ask > rangeHigh + buffer;
   bool sellSignal = bid < rangeLow  - buffer;
   if(!buySignal && !sellSignal) return;

   bool isBuy = buySignal;
   if(!SwingFilterOk(isBuy)) return;

   // Stop at opposite side of the range (classic range-breakout stop)
   double entry = isBuy ? ask : bid;
   double sl    = isBuy ? rangeLow - buffer : rangeHigh + buffer;
   double dist  = MathAbs(entry - sl);
   double lots  = LotsForRisk(dist);
   if(lots <= 0) { Print("Lot size below minimum for risk - skipping"); return; }

   double tp = 0.0;
   if(InpFinalTpR > 0) tp = isBuy ? entry + dist * InpFinalTpR : entry - dist * InpFinalTpR;
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   // Store initial risk distance in the comment so partial TP can compute R after restarts
   string comment = StringFormat("RBO R=%.5f", dist);
   bool ok = isBuy ? trade.Buy(lots, _Symbol, 0.0, sl, tp, comment)
                   : trade.Sell(lots, _Symbol, 0.0, sl, tp, comment);
   if(ok) tradedToday = true;
   else   PrintFormat("Order failed: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Management: partial TP + ATR trailing stop                       |
//+------------------------------------------------------------------+
void ManagePositions()
  {
   double atr = GetATR();
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double minVol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol ||
         PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;

      bool   isBuy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double open  = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double vol   = PositionGetDouble(POSITION_VOLUME);
      double price = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                           : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      // Parse initial risk distance from comment "RBO R=<dist>"
      string c = PositionGetString(POSITION_COMMENT);
      double rDist = 0.0;
      int p = StringFind(c, "R=");
      if(p >= 0) rDist = StringToDouble(StringSubstr(c, p + 2));
      double profitDist = isBuy ? price - open : open - price;

      // --- Partial TP: once, detected by SL not yet at/through breakeven
      bool slBelowBE = isBuy ? (sl < open) : (sl > open || sl == 0.0);
      if(rDist > 0 && slBelowBE && profitDist >= rDist * InpPartialAtR)
        {
         double closeVol = NormalizeLots(vol * InpPartialPercent / 100.0);
         if(closeVol >= minVol && vol - closeVol >= minVol)
            trade.PositionClosePartial(ticket, closeVol);
         // Move stop to breakeven so the partial is done once and the trade is risk-free
         trade.PositionModify(ticket, NormalizeDouble(open, digits), tp);
         continue;
        }

      // --- ATR trailing stop (only tightens, never loosens)
      if(atr > 0)
        {
         double newSl = isBuy ? price - atr * InpAtrTrailMult : price + atr * InpAtrTrailMult;
         newSl = NormalizeDouble(newSl, digits);
         bool better = isBuy ? (newSl > sl + _Point) : (sl == 0.0 || newSl < sl - _Point);
         bool inProfit = isBuy ? newSl > open : newSl < open;
         if(better && inProfit) trade.PositionModify(ticket, newSl, tp);
        }
     }
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   bool canTrade = RiskGuardsOk();
   ManagePositions();          // always manage open trades, even when halted
   if(!canTrade) return;
   BuildRange();
   CheckEntry();
  }
//+------------------------------------------------------------------+
