"""Causal, shared long/cash trend-pullback and mean-reversion strategy.

The defaults incorporate dynamic volatility trailing stops, profit locking,
and trend breakdown protection. Orders use the next bar's open. The strategy's
exits are close-based decisions, not intraday guaranteed stop prices. No ticker
or benchmark enters the signal calculation.
"""
from __future__ import annotations

from numbers import Integral, Real

import numpy as np
import pandas as pd

from strategy_base import StrategyBase


class AdaptiveRegimeStrategy(StrategyBase):
    """Buy pullbacks in an uptrend, or oversold conditions outside an uptrend.

    Uptrend: EMA(fast) > EMA(slow) and close > EMA(slow).
    Entry: (uptrend and RSI < pullback) or RSI < oversold, subject to cooldown.
    Exit: outside the uptrend, RSI > overbought or close >= EMA(mean).
    Risk exit: close < trail or close < entry * (1 - stop_loss_pct), where trail
    starts at entry open and tracks highest subsequent close minus ATR * multiplier.
    When trade gain exceeds profit_threshold, the trail tightens to
    profit_atr_multiplier to lock in large trend profits (e.g. rallies in ASELS/AKBNK).
    Trend break exit: close < slow EMA when a trend position loses its uptrend structure.

    ``Signal`` expresses persistent desired exposure: 1 means long and -1
    means cash. The warmup emits 0. Repeated long signals also permit the
    engine to re-enter after an optional external risk exit. Internal state
    tracks the strategy's desired position, independently of such overrides.
    """

    def __init__(
        self,
        fast_period: int = 15,
        slow_period: int = 50,
        rsi_period: int = 3,
        oversold: float = 20.0,
        pullback: float = 50.0,
        overbought: float = 70.0,
        mean_period: int = 10,
        atr_period: int = 14,
        atr_multiplier: float = 3.5,
        profit_atr_multiplier: float = 2.3,
        profit_threshold: float = 0.20,
        stop_loss_pct: float = 0.08,
        exit_on_slow_break: bool = True,
        cooldown_bars: int = 1,
        warmup_period: int = 50,
    ):
        periods = dict(fast_period=fast_period, slow_period=slow_period,
                       rsi_period=rsi_period, mean_period=mean_period,
                       atr_period=atr_period, warmup_period=warmup_period,
                       cooldown_bars=cooldown_bars)
        for name, value in periods.items():
            if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
            if name != "cooldown_bars" and value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        if warmup_period < max(slow_period, mean_period, rsi_period + 1, atr_period):
            raise ValueError("warmup_period must cover every indicator period")
        levels = dict(oversold=oversold, pullback=pullback,
                      overbought=overbought, atr_multiplier=atr_multiplier,
                      profit_atr_multiplier=profit_atr_multiplier,
                      profit_threshold=profit_threshold,
                      stop_loss_pct=stop_loss_pct)
        for name, value in levels.items():
            if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0 < oversold < pullback < overbought < 100:
            raise ValueError("thresholds must satisfy 0 < oversold < pullback < overbought < 100")
        if atr_multiplier <= 0 or profit_atr_multiplier <= 0:
            raise ValueError("atr multipliers must be positive")
        if stop_loss_pct < 0:
            raise ValueError("stop_loss_pct must be non-negative")
        if profit_threshold <= 0:
            raise ValueError("profit_threshold must be positive")
        if not isinstance(exit_on_slow_break, bool):
            raise ValueError("exit_on_slow_break must be boolean")
        params = {**periods, **levels, "exit_on_slow_break": exit_on_slow_break}
        super().__init__(name="Adaptive_Regime", params=params)
        for name, value in params.items():
            setattr(self, name, value)

    def set_params(self, **kwargs):
        """Apply validated parameters atomically, including their attributes."""
        candidate = type(self)(**{**self.get_params(), **kwargs})
        self.__dict__.update(candidate.__dict__)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        required = ["Open", "High", "Low", "Close"]
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
        if not df.index.is_unique or not df.index.is_monotonic_increasing:
            raise ValueError("OHLC index must be unique and increasing")
        prices = df[required].to_numpy(dtype=float)
        if not np.isfinite(prices).all() or (prices <= 0).any():
            raise ValueError("OHLC prices must be finite and positive")
        out = df.copy(deep=True)
        close = out["Close"]
        for period in {self.fast_period, self.slow_period, self.mean_period}:
            out[f"EMA_{period}"] = close.ewm(span=period, adjust=False,
                                              min_periods=period).mean()
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / self.rsi_period, adjust=False,
                                      min_periods=self.rsi_period).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / self.rsi_period, adjust=False,
                                       min_periods=self.rsi_period).mean()
        # A strictly rising market has RSI=100; a flat market has RSI=50.
        denom = gain + loss
        out[f"RSI_{self.rsi_period}"] = np.where(denom > 1e-10, 100 * gain / denom, 50.0)
        true_range = pd.concat([
            out.High - out.Low,
            (out.High - close.shift()).abs(),
            (out.Low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        out["ATR"] = true_range.ewm(alpha=1 / self.atr_period, adjust=False,
                                    min_periods=self.atr_period).mean()
        out[f"ATR_{self.atr_period}"] = out["ATR"]
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy(deep=True)
        length = len(out)
        signals = np.zeros(length, dtype=int)
        targets = np.zeros(length, dtype=int)
        regimes = np.full(length, "warmup", dtype=object)
        entry_reasons = np.full(length, "", dtype=object)
        exit_reasons = np.full(length, "", dtype=object)
        trails = np.full(length, np.nan)

        # These are local to every run: one instance can safely serve all stocks.
        held = False
        pending = 0
        peak = 0.0
        entry_price = 0.0
        entry_is_trend = False
        bars_since_exit = 999
        opens = out.Open.to_numpy()
        closes = out.Close.to_numpy()
        fast = out[f"EMA_{self.fast_period}"].to_numpy()
        slow = out[f"EMA_{self.slow_period}"].to_numpy()
        mean = out[f"EMA_{self.mean_period}"].to_numpy()
        rsi = out[f"RSI_{self.rsi_period}"].to_numpy()
        atr = out.ATR.to_numpy()

        for i in range(length):
            # An order from the previous close first becomes a position here.
            if pending == 1:
                held = True
                peak = float(opens[i])
                entry_price = float(opens[i])
                entry_is_trend = (regimes[i - 1] == "uptrend") if i > 0 else False
            elif pending == -1:
                held = False
                bars_since_exit = 0
            pending = 0

            if not held:
                bars_since_exit += 1
            if held:
                peak = max(peak, float(closes[i]))
                gain_pct = (peak / entry_price - 1.0) if entry_price > 0 else 0.0
                mult = self.profit_atr_multiplier if gain_pct >= self.profit_threshold else self.atr_multiplier
                trails[i] = peak - mult * atr[i]

            if i < self.warmup_period - 1:
                continue

            trend = fast[i] > slow[i] and closes[i] > slow[i]
            regimes[i] = "uptrend" if trend else "range_or_downtrend"

            buy_trend = trend and rsi[i] < self.pullback
            buy_os = rsi[i] < self.oversold
            buy = (buy_trend or buy_os) and (bars_since_exit >= self.cooldown_bars)

            recovery_exit = not trend and (rsi[i] > self.overbought or closes[i] >= mean[i])
            risk_exit = held and (closes[i] < trails[i] or (self.stop_loss_pct > 0 and closes[i] < entry_price * (1 - self.stop_loss_pct)))
            trend_exit = held and self.exit_on_slow_break and (closes[i] < slow[i] and not trend)

            if held and (recovery_exit or risk_exit or trend_exit):
                pending = -1
                signals[i] = -1
                if risk_exit:
                    exit_reasons[i] = "close_atr_stop"
                elif trend_exit:
                    exit_reasons[i] = "trend_break_exit"
                else:
                    exit_reasons[i] = "mean_reversion_exit"
            elif not held and buy:
                pending = 1
                signals[i] = 1
                targets[i] = 1
                entry_reasons[i] = "trend_pullback" if trend else "oversold"
            elif held:
                signals[i] = 1
                targets[i] = 1
            else:
                signals[i] = -1

        out["Signal"] = signals
        out["Target_Position"] = targets
        out["Regime"] = regimes
        out["Entry_Reason"] = entry_reasons
        out["Exit_Reason"] = exit_reasons
        out["Strategy_Exit"] = exit_reasons
        out["Close_Trail"] = trails
        return out
