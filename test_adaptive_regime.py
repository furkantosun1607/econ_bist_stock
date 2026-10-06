"""Timing, causality and state-isolation checks for the shared strategy."""
import unittest
from unittest.mock import patch

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
        for n in (30, 49, 50, 59, 60, 91, 153, 247):
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
        warmup_end = self.strategy.warmup_period - 1
        self.assertTrue((out.Signal.iloc[:warmup_end] == 0).all())
        self.assertTrue((out.Target_Position.iloc[:warmup_end] == 0).all())
        self.assertTrue((out.Regime.iloc[:warmup_end] == "warmup").all())

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
                                          rsi_period=1, atr_period=1, warmup_period=2,
                                          exit_on_slow_break=False)
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
                                          rsi_period=1, atr_period=1, atr_multiplier=5.0,
                                          warmup_period=2, stop_loss_pct=0)
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

    def test_profit_lock_remains_active_after_peak_gain_in_strong_trend(self):
        strategy = AdaptiveRegimeStrategy(
            fast_period=1, slow_period=2, mean_period=1, rsi_period=1,
            atr_period=1, warmup_period=2, stop_loss_pct=0,
        )
        df = strategy.prepare_data(market([100, 99, 125, 119, 118]))
        df["Open"] = [100, 100, 100, 125, 119]
        df["EMA_1"] = 90
        df["EMA_2"] = 80
        df["RSI_1"] = [50, 10, 80, 80, 80]
        df["ATR"] = 2
        out = strategy.generate_signals(df)
        # Still an uptrend; peak gain, not current gain, keeps the lock active.
        self.assertEqual(out.Regime.iloc[3], "uptrend")
        self.assertAlmostEqual(out.Close_Trail.iloc[3], 120.4)
        self.assertEqual(out.Signal.iloc[3], -1)
        self.assertEqual(out.Strategy_Exit.iloc[3], "close_atr_stop")
        strategy.set_params(profit_threshold=.50)
        unlocked = strategy.generate_signals(df)
        self.assertEqual(unlocked.Signal.iloc[3], 1)

    def test_slow_break_exits_on_first_close_even_for_oversold_entry(self):
        strategy = AdaptiveRegimeStrategy(
            fast_period=1, slow_period=2, mean_period=1, rsi_period=1,
            atr_period=1, warmup_period=2,
        )
        df = strategy.prepare_data(market([100, 99, 99, 98]))
        df["EMA_1"] = 104
        df["EMA_2"] = 105
        df["RSI_1"] = [50, 10, 10, 10]
        df["ATR"] = 100
        out = strategy.generate_signals(df)
        self.assertEqual(out.Entry_Reason.iloc[1], "oversold")
        self.assertEqual(out.Signal.iloc[2], -1)
        self.assertEqual(out.Strategy_Exit.iloc[2], "trend_break_exit")
        strategy.set_params(exit_on_slow_break=False)
        self.assertEqual(strategy.generate_signals(df).Signal.iloc[2], 1)

    def test_percentage_stop_is_a_close_trigger_not_a_guaranteed_fill(self):
        strategy = AdaptiveRegimeStrategy(
            fast_period=1, slow_period=2, mean_period=1, rsi_period=1,
            atr_period=1, warmup_period=2,
        )
        df = strategy.prepare_data(market([100, 99, 91, 90]))
        df["Open"] = [100, 100, 100, 85]
        df["High"] = 101
        df["Low"] = 84
        df["EMA_1"] = 80
        df["EMA_2"] = 70
        df["RSI_1"] = [50, 10, 50, 80]
        df["ATR"] = 20
        out = strategy.generate_signals(df)
        self.assertEqual(out.Strategy_Exit.iloc[2], "close_stop_loss")
        result = Backtester().run(out)
        self.assertEqual(result.trades[0].entry_price, 100)
        self.assertEqual(result.trades[0].exit_price, 85)
        self.assertEqual(result.trades[0].pnl_pct, -15)
        self.assertEqual(result.final_capital, 85000)
        strategy.set_params(stop_loss_pct=0)
        self.assertEqual(strategy.generate_signals(df).Signal.iloc[2], 1)

    def test_cooldown_counts_closes_after_exit_open(self):
        strategy = AdaptiveRegimeStrategy(
            fast_period=1, slow_period=2, mean_period=1, rsi_period=1,
            atr_period=1, warmup_period=2, cooldown_bars=3,
        )
        df = strategy.prepare_data(market([100, 99, 99, 99, 99, 99]))
        df["EMA_1"] = 104
        df["EMA_2"] = 105
        df["RSI_1"] = 10
        df["ATR"] = 100
        self.assertEqual(strategy.generate_signals(df).Signal.tolist(),
                         [0, 1, -1, -1, -1, 1])

    def test_default_and_cli_risk_settings_use_one_strategy_profile(self):
        from runner import main

        scenarios = [([], {"atr_multiplier": 3.5, "profit_atr_multiplier": 2.3,
                           "profit_threshold": .20, "stop_loss_pct": .07}),
                     (["--atr-multiplier", "4", "--profit-atr-multiplier", "2",
                       "--profit-threshold", "0.30", "--strategy-stop-loss", "0.06"],
                      {"atr_multiplier": 4, "profit_atr_multiplier": 2,
                       "profit_threshold": .30, "stop_loss_pct": .06})]
        for arguments, expected in scenarios:
            with self.subTest(arguments=arguments):
                with patch("runner.run_pipeline", return_value=({}, {}, pd.DataFrame())) as run:
                    with patch("sys.argv", ["runner.py", "--no-charts", *arguments]):
                        with self.assertRaises(SystemExit) as stopped:
                            main()
                    self.assertEqual(stopped.exception.code, 0)
                    used = run.call_args.kwargs["strategy"]
                    for name, value in expected.items():
                        self.assertEqual(used.get_params()[name], value)
                    self.assertEqual(used.fast_period, 15)
                    self.assertEqual(used.slow_period, 50)
                    self.assertEqual(used.warmup_period, 50)
                    self.assertTrue(used.exit_on_slow_break)
                    self.assertIsNone(run.call_args.kwargs["risk_manager"])

    def test_signal_does_not_depend_on_symbol_or_capital(self):
        renamed = self.df.copy()
        renamed.attrs["ticker"] = "UNSEEN"
        renamed.attrs["benchmark"] = 1000000000
        assert_frame_equal(self.strategy.run(self.df), self.strategy.run(renamed))

    def test_invalid_parameters(self):
        for params in ({"fast_period": 0}, {"slow_period": 15}, {"rsi_period": 2.5},
                       {"mean_period": True}, {"atr_multiplier": 0},
                       {"atr_multiplier": np.nan}, {"oversold": 55},
                       {"overbought": 100}, {"warmup_period": 10},
                       {"stop_loss_pct": -0.01}, {"stop_loss_pct": 1},
                       {"profit_threshold": 0}, {"profit_atr_multiplier": 4},
                       {"profit_atr_multiplier": np.inf}, {"cooldown_bars": -1},
                       {"cooldown_bars": True}, {"exit_on_slow_break": 1}):
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
