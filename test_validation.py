"""Regression tests for cash-reset chronological evaluation boundaries."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from backtester import BacktestResult
from validate_strategy import evaluate_window, run_validation


def boundary_signals():
    # The pre-window rally and post-window jump must not contribute any P&L.
    frame = pd.DataFrame(
        {
            "Open": [10, 900, 100, 125, 5000],
            "High": [900, 1000, 120, 130, 5100],
            "Low": [10, 899, 95, 124, 4999],
            "Close": [900, 1000, 110, 130, 5050],
            "Volume": [100_000] * 5,
            "Signal": [1, 1, -1, 0, 0],
        },
        index=pd.to_datetime([
            "2025-12-30", "2025-12-31", "2026-01-02", "2026-01-05", "2026-01-06"
        ]),
    )
    frame.index.name = "Date"
    return frame


class FixedLongStrategy:
    """An untrained fixed policy used only to test the validation pipeline."""

    def __init__(self):
        self.calls = 0

    def run(self, frame):
        self.calls += 1
        result = frame.copy()
        result["Signal"] = 1
        return result

    def get_name(self):
        return "FixedLong"

    def get_params(self):
        return {}


class TestValidation(unittest.TestCase):
    def test_prior_close_signal_enters_first_open_without_prior_profit(self):
        frame = boundary_signals()
        result = evaluate_window(
            frame, "AKBNK.IS", "Boundary", "2026-01-01", "2026-01-06"
        )
        # 1,000 shares bought at the first evaluation open (100), sold at 125.
        self.assertEqual(result["final_capital"], 125_000)
        self.assertEqual(result["return_pct"], 25.0)
        self.assertEqual(result["trades"], 1)
        self.assertEqual(result["buy_hold_final"], 130_000)
        self.assertEqual(result["start"], "2026-01-02")
        self.assertEqual(result["end"], "2026-01-05")
        self.assertEqual(result["bars"], 2)
        # The observation row conveys its decision, never a price return.
        frame.loc[:"2025-12-31", ["Open", "High", "Low", "Close"]] *= 10
        changed = evaluate_window(
            frame, "AKBNK.IS", "Boundary", "2026-01-01", "2026-01-06"
        )
        self.assertEqual(result, changed)

    def test_first_evaluation_close_cannot_trade_its_own_open(self):
        frame = boundary_signals()
        frame["Signal"] = [1, 0, 1, 0, 0]
        result = evaluate_window(
            frame, "AKBNK.IS", "Boundary", "2026-01-01", "2026-01-06"
        )
        # The first in-window signal enters the second open: 800 shares at 125.
        self.assertEqual(result["final_capital"], 104_000)
        self.assertEqual(result["trades"], 1)

    def test_exclusive_end_liquidates_before_outside_price_jump(self):
        frame = boundary_signals()
        frame["Signal"] = [1, 1, 0, -1, 0]
        result = evaluate_window(
            frame, "AKBNK.IS", "Boundary", "2026-01-01", "2026-01-06"
        )
        self.assertEqual(result["final_capital"], 130_000)
        self.assertEqual(result["trades"], 1)

    def test_cost_stress_retains_residual_cash_and_charges_both_sides(self):
        frame = boundary_signals()
        frame.loc["2026-01-05", ["Open", "High", "Low", "Close"]] = [110, 111, 109, 110]
        frame["Signal"] = [0, 1, 0, 0, 0]
        result = evaluate_window(
            frame, "AKBNK.IS", "Stress", "2026-01-01", "2026-01-06",
            commission=.001, slippage=.001,
        )
        # Entry: 998 * 100.1 + 99.8998 commission; 0.3002 cash remains.
        # Exit: 998 * 109.89 - 109.67022 commission = 109560.54978.
        self.assertEqual(result["final_capital"], 109_560.85)
        self.assertEqual(result["buy_hold_final"], 109_560.85)
        self.assertAlmostEqual(result["excess_vs_buy_hold_tl"], 0, places=2)
        self.assertGreater(result["max_drawdown_pct"], 0)

    def test_window_evaluation_never_compares_full_period_benchmarks(self):
        with patch.object(
            BacktestResult, "compare_with_benchmark",
            side_effect=AssertionError("Subperiod benchmark comparison is invalid"),
        ):
            result = evaluate_window(
                boundary_signals(), "AKBNK.IS", "Boundary", "2026-01-01", "2026-01-06"
            )
        self.assertFalse({"passed", "fully_passed", "benchmark_final"}.intersection(result))

    def test_validation_reuses_fixed_signals_and_writes_window_reports(self):
        dates = pd.bdate_range("2025-01-01", "2026-07-06")
        frame = pd.DataFrame(
            {"Open": 100., "High": 101., "Low": 99., "Close": 100., "Volume": 100_000},
            index=dates,
        )
        strategy = FixedLongStrategy()
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            BacktestResult, "compare_with_benchmark",
            side_effect=AssertionError("Validation must not use challenge scores"),
        ):
            summary = run_validation(
                strategy, all_data={"SYNTHETIC.IS": frame}, output_dir=temp_dir
            )
            self.assertEqual(strategy.calls, 1)
            self.assertEqual(len(summary), 12)  # Two strategies, six evaluations.
            self.assertEqual(len(summary[summary["strategy"] == "FixedLong"]), 6)
            self.assertFalse({"passed", "fully_passed", "benchmark_final"}.intersection(summary))
            self.assertTrue((Path(temp_dir) / "summary.csv").exists())
            self.assertTrue((Path(temp_dir) / "report.md").exists())
            manifest = json.loads((Path(temp_dir) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["execution"], "next_open")
            self.assertEqual(manifest["development_end_exclusive"], "2026-01-01")
            self.assertEqual(manifest["parameters"], {})
            self.assertIsNone(manifest["data"]["SYNTHETIC.IS"]["cache_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
