//+------------------------------------------------------------------+
//| SwingFib.mqh                                                     |
//| ZigZag-style swing detection + Fibonacci retracement levels.     |
//| Self-contained (does not depend on the built-in ZigZag indicator)|
//| Educational code - UNCOMPILED in CI, verify in MetaEditor.       |
//+------------------------------------------------------------------+
#property strict
#ifndef SWINGFIB_MQH
#define SWINGFIB_MQH

struct SwingPoint
  {
   datetime time;
   double   price;
   bool     isHigh;   // true = swing high, false = swing low
   int      shift;    // bar index (series order, 0 = current bar)
  };

//--- A bar is a swing high if its high is the highest of `depth` bars on each side.
bool IsSwingHigh(const string sym, ENUM_TIMEFRAMES tf, int shift, int depth)
  {
   double h = iHigh(sym, tf, shift);
   for(int i = 1; i <= depth; i++)
     {
      if(iHigh(sym, tf, shift + i) > h) return false;
      if(shift - i >= 0 && iHigh(sym, tf, shift - i) >= h) return false;
     }
   return true;
  }

bool IsSwingLow(const string sym, ENUM_TIMEFRAMES tf, int shift, int depth)
  {
   double l = iLow(sym, tf, shift);
   for(int i = 1; i <= depth; i++)
     {
      if(iLow(sym, tf, shift + i) < l) return false;
      if(shift - i >= 0 && iLow(sym, tf, shift - i) <= l) return false;
     }
   return true;
  }

//--- Find the most recent N alternating swings (ZigZag-like), newest first.
//--- Only confirmed swings are used (shift >= depth) so there is no repainting.
int FindSwings(const string sym, ENUM_TIMEFRAMES tf, int depth, int lookback,
               SwingPoint &out[], int maxSwings = 4)
  {
   ArrayResize(out, 0);
   int count = 0;
   int bars = MathMin(lookback, Bars(sym, tf) - depth - 1);
   for(int s = depth; s < bars && count < maxSwings; s++)
     {
      bool hi = IsSwingHigh(sym, tf, s, depth);
      bool lo = IsSwingLow(sym, tf, s, depth);
      if(!hi && !lo) continue;
      bool isHigh = hi; // if both (outside bar), prefer high
      double price = isHigh ? iHigh(sym, tf, s) : iLow(sym, tf, s);
      if(count > 0 && out[count - 1].isHigh == isHigh)
        {
         // same type in a row: keep the more extreme one (ZigZag rule)
         bool better = isHigh ? (price > out[count - 1].price) : (price < out[count - 1].price);
         if(better)
           {
            out[count - 1].price = price;
            out[count - 1].time  = iTime(sym, tf, s);
            out[count - 1].shift = s;
           }
         continue;
        }
      ArrayResize(out, count + 1);
      out[count].price  = price;
      out[count].time   = iTime(sym, tf, s);
      out[count].isHigh = isHigh;
      out[count].shift  = s;
      count++;
     }
   return count;
  }

//--- Fibonacci retracement price between swing `from` and swing `to`.
//--- ratio 0.0 = `to` price, 1.0 = `from` price (classic retracement convention).
double FibLevel(double fromPrice, double toPrice, double ratio)
  {
   return toPrice - (toPrice - fromPrice) * ratio;
  }

//--- Is price inside the [lowRatio, highRatio] retracement zone of the last leg?
//--- For an up leg (low->high) this is a pullback buy zone; for a down leg, a sell zone.
bool InFibZone(const SwingPoint &legStart, const SwingPoint &legEnd, double price,
               double lowRatio = 0.5, double highRatio = 0.618)
  {
   double a = FibLevel(legStart.price, legEnd.price, lowRatio);
   double b = FibLevel(legStart.price, legEnd.price, highRatio);
   return price >= MathMin(a, b) && price <= MathMax(a, b);
  }

#endif
