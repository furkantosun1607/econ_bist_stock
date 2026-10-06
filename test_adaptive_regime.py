"""Timing, causality and state-isolation checks for the shared strategy."""
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from backtester import Backtester
from strategies.adaptive_regime import AdaptiveRegimeStrategy


def market(close):
    close = np.asarray(close, dtype=float)
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"Open": opening,
                         "High": np.maximum(opening, close) + 1,
                         "Low": np.minimum(opening, close) - 1,
                         "Close": close, "Volume": 100000},
                        index=pd.bdate_range("2020-01-01", periods=len(close)))


class TestAdaptiveRegime(unittest.TestCase):
    def setUp(self):
        t = np.arange(300)
        self.df = market(100 + .06 * t + 8 * np.sin(t / 7) + 2 * np.sin(t / 2))
        self.strategy = AdaptiveRegimeStrategy()

    def test_prefix_invariance(self):
        full = self.strategy.run(self.df)
        for n in (30, 59, 60, 91, 153, 247):
            with self.subTest(n=n):
                assert_frame_equal(full.iloc[:n], self.strategy.run(self.df.iloc[:n]))

    def test_future_mutation_does_not_change_history(self):
        changed = self.df.copy()
        changed.loc[changed.index[160:], ["Open", "High", "Low", "Close"]] *= 3
        assert_frame_equal(self.strategy.run(self.df).iloc[:160],
                           self.strategy.run(changed).iloc[:160])

    def test_reuse_and_no_input_mutation(self):
        original = self.df.copy(deep=True)
        first = self.strategy.run(self.df)
        self.strategy.run(market(np.linspace(200, 100, 100)))
        assert_frame_equal(first, self.strategy.run(self.df))
        assert_frame_equal(original, self.df)

    def test_warmup_has_no_exposure(self):
        out = self.strategy.run(self.df)
        self.assertTrue((out.Signal.iloc[:59] == 0).all())
        self.assertTrue((out.Target_Position.iloc[:59] == 0).all())
        self.assertTrue((out.Regime.iloc[:59] == "warmup").all())

    def test_monotonic_rsi_and_flat_prices(self):
        rising = self.strategy.run(market(np.arange(100, 200)))
        falling = self.strategy.run(market(np.arange(200, 100, -1)))
        flat = self.strategy.run(market(np.full(100, 100)))
        self.assertEqual(rising.RSI_3.iloc[-1], 100)
        self.assertEqual(falling.RSI_3.iloc[-1], 0)
        self.assertEqual(flat.RSI_3.iloc[-1], 50)
        self.assertEqual(rising.Regime.iloc[-1], "uptrend")
        self.assertFalse((rising.Signal == 1).any())  # Pullback required.
        self.assertTrue((falling.Signal == 1).any())

    def test_persistent_signal_and_range_recovery(self):
        strategy = AdaptiveRegimeStrategy(fast_period=1, slow_period=2, mean_period=1,
                                          rsi_period=1, atr_period=1, warmup_period=2)
        df = strategy.prepare_data(market([100, 99, 103, 103]))
        df["EMA_1"] = 104
        df["EMA_2"] = 105
        df["RSI_1"] = [50, 10, 10, 90]
        df["ATR"] = 1
        out = strategy.generate_signals(df)
        self.assertEqual(out.Signal.tolist(), [0, 1, 1, -1])
        self.assertEqual(out.Strategy_Exit.iloc[-1], "mean_reversion_exit")
        self.assertEqual(out.Target_Position.tolist(), [0, 1, 1, 0])

    def test_close_stop_executes_at_following_open(self):
        strategy = AdaptiveRegimeStrategy(fast_period=1, slow_period=2, mean_period=1,
                                          rsi_period=1, atr_period=1, warmup_period=2)
        df = strategy.prepare_data(market([100, 99, 90, 91]))
        df["Open"] = [100, 100, 100, 91]
        df["High"] = 101
        df["Low"] = 89
        df["EMA_1"] = 104
        df["EMA_2"] = 105
        df["RSI_1"] = [50, 10, 10, 90]
        df["ATR"] = 1
        out = strategy.generate_signals(df)
        self.assertEqual(out.Signal.tolist(), [0, 1, -1, -1])
        self.assertEqual(out.Strategy_Exit.iloc[2], "close_atr_stop")
        self.assertEqual(out.Close_Trail.iloc[2], 95)
        result = Backtester().run(out)
        self.assertEqual(result.trades[0].entry_price, 100)
        self.assertEqual(result.trades[0].exit_price, 91)
        self.assertEqual(result.final_capital, 91000)

    def test_signal_does_not_depend_on_symbol_or_capital(self):
        renamed = self.df.copy()
        renamed.attrs["ticker"] = "UNSEEN"
        renamed.attrs["benchmark"] = 1000000000
        assert_frame_equal(self.strategy.run(self.df), self.strategy.run(renamed))

    def test_invalid_parameters(self):
        for params in ({"fast_period": 0}, {"slow_period": 20}, {"rsi_period": 2.5},
                       {"mean_period": True}, {"atr_multiplier": 0},
                       {"atr_multiplier": np.nan}, {"oversold": 50},
                       {"overbought": 100}, {"warmup_period": 10}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                AdaptiveRegimeStrategy(**params)

    def test_parameter_update_is_validated_and_atomic(self):
        before = self.strategy.get_params()
        with self.assertRaises(ValueError):
            self.strategy.set_params(atr_multiplier=-2)
        self.assertEqual(before, self.strategy.get_params())
        self.strategy.set_params(atr_multiplier=4)
        self.assertEqual(self.strategy.atr_multiplier, 4)
        self.assertEqual(self.strategy.get_params()["atr_multiplier"], 4)

    def test_invalid_prices_and_time_order(self):
        for df in (self.df.iloc[::-1], pd.concat([self.df, self.df]),
                   self.df.assign(Close=np.nan), self.df.assign(Open=0),
                   self.df.drop(columns="High")):
            with self.assertRaises(ValueError):
                self.strategy.run(df)

    def test_short_and_empty_frames(self):
        for n in (0, 1, 20):
            out = self.strategy.run(self.df.iloc[:n])
            self.assertEqual(len(out), n)
            self.assertTrue((out.Signal == 0).all())


if __name__ == "__main__":
    unittest.main()
