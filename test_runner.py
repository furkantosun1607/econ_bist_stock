"""
Unit Test Suite for Runner Module and Notebook (Phase 8)
=========================================================
Test senaryolari:
1. Strategy Registry (get_strategy, register_strategy)
2. run_pipeline fonksiyonunun tek veya coklu hisse uzerinde calismasi
3. CLI argument parser parametrlerinin dogrulugu
4. main_notebook.ipynb dosya yapisi ve gecerliligi
"""

import json
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import pandas as pd

from runner import (
    STRATEGIES,
    build_parser,
    get_strategy,
    register_strategy,
    run_pipeline,
)
from strategies.sma_crossover import SmaCrossoverStrategy
from strategies.adaptive_regime import AdaptiveRegimeStrategy
from strategy_base import StrategyBase


class DummyStrategy(StrategyBase):
    def __init__(self, param=1):
        super().__init__(name="DummyStrategy", params={"param": param})

    def generate_signals(self, df):
        df = df.copy()
        df["Signal"] = 0
        return df


class TestRunner(unittest.TestCase):

    def test_strategy_registry(self):
        """Strateji kayit ve cagirma mekanizmasi."""
        register_strategy("dummy", DummyStrategy)
        self.assertIn("dummy", STRATEGIES)

        s = get_strategy("dummy", param=5)
        self.assertEqual(s.get_name(), "DummyStrategy")
        self.assertEqual(s.get_params()["param"], 5)

        # Bilinmeyen strateji hatasi
        with self.assertRaises(ValueError):
            get_strategy("non_existent_strategy")

    def test_cli_parser(self):
        """CLI arguman parser seceneklerinin dogrulugu."""
        parser = build_parser()
        args = parser.parse_args([
            "--fast", "15",
            "--slow", "60",
            "--stop-loss", "0.06",
            "--trailing-stop", "0.04",
            "--mode", "same_close",
            "--no-charts",
        ])
        self.assertEqual(args.fast, 15)
        self.assertEqual(args.slow, 60)
        self.assertEqual(args.stop_loss, 0.06)
        self.assertEqual(args.trailing_stop, 0.04)
        self.assertEqual(args.mode, "same_close")
        self.assertTrue(args.no_charts)
        self.assertEqual(parser.parse_args([]).strategy, "adaptive_regime")
        self.assertIsNone(parser.parse_args([]).trailing_stop)
        self.assertIsInstance(get_strategy("adaptive_regime"), AdaptiveRegimeStrategy)

    @patch("runner.load_stock_data")
    def test_run_pipeline_single_stock(self, load):
        """run_pipeline fonksiyonunun tek hisse uzerinde basariyla donmesi."""
        strategy = SmaCrossoverStrategy(10, 50)
        close = 100 + np.sin(np.arange(120) / 10) * 15
        load.return_value = pd.DataFrame({
            "Open": close, "Close": close, "High": close + 1,
            "Low": close - 1, "Volume": 1000,
        }, index=pd.bdate_range("2025-01-02", periods=120))
        results, challenge_eval, df_summary = run_pipeline(
            strategy=strategy,
            stocks=["AKBNK.IS"],
            save_charts=False,
            save_trades=False,
            save_metrics=False,
            print_summary=False,
        )
        self.assertIn("AKBNK.IS", results)
        self.assertEqual(len(df_summary), 1)
        self.assertIn("all_passed", challenge_eval)

    @patch("runner.load_stock_data")
    def test_run_pipeline_adaptive_regime(self, load):
        """run_pipeline fonksiyonunun AdaptiveRegimeStrategy ile ucuca calismasi."""
        strategy = AdaptiveRegimeStrategy()
        n = 150
        close = 100 + np.sin(np.arange(n) / 5) * 15 + np.arange(n) * 0.1
        load.return_value = pd.DataFrame({
            "Open": close, "Close": close, "High": close + 2,
            "Low": close - 2, "Volume": 10000,
        }, index=pd.bdate_range("2025-01-02", periods=n))
        results, challenge_eval, df_summary = run_pipeline(
            strategy=strategy,
            stocks=["AKBNK.IS"],
            save_charts=False,
            save_trades=False,
            save_metrics=False,
            print_summary=False,
        )
        self.assertIn("AKBNK.IS", results)
        self.assertEqual(len(df_summary), 1)
        self.assertIn("all_passed", challenge_eval)
        self.assertEqual(results["AKBNK.IS"].strategy_name, "Adaptive_Regime")

    def test_adaptive_rejects_same_close_execution(self):
        with self.assertRaisesRegex(ValueError, "next_open"):
            run_pipeline(AdaptiveRegimeStrategy(), execution_mode="same_close",
                         save_charts=False, save_metrics=False, save_trades=False)

    @patch("runner.run_pipeline")
    def test_cli_main_adaptive_regime(self, mock_run):
        """CLI main() fonksiyonunun varsayilan adaptive_regime ile calismasi."""
        from runner import main
        mock_run.return_value = ({}, {}, pd.DataFrame())
        with patch("sys.argv", ["runner.py", "--no-charts", "--no-trades"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(mock_run.called)
        called_strategy = mock_run.call_args[1]["strategy"]
        self.assertIsInstance(called_strategy, AdaptiveRegimeStrategy)

    @patch("runner.run_pipeline")
    def test_cli_main_sma_crossover(self, mock_run):
        """CLI main() fonksiyonunun --strategy sma_crossover ile calismasi."""
        from runner import main
        mock_run.return_value = ({}, {}, pd.DataFrame())
        with patch("sys.argv", ["runner.py", "--strategy", "sma_crossover", "--fast", "12", "--slow", "45", "--no-charts"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
        self.assertTrue(mock_run.called)
        called_strategy = mock_run.call_args[1]["strategy"]
        self.assertIsInstance(called_strategy, SmaCrossoverStrategy)
        self.assertEqual(called_strategy.get_params()["fast_period"], 12)
        self.assertEqual(called_strategy.get_params()["slow_period"], 45)

    def test_notebook_format_and_cells(self):
        """main_notebook.ipynb dosyasinin standart Jupyter formati ve ciktilarini dogrula."""
        nb_path = Path("main_notebook.ipynb")
        self.assertTrue(nb_path.exists())

        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        self.assertEqual(nb.get("nbformat"), 4)
        self.assertIn("cells", nb)
        self.assertGreater(len(nb["cells"]), 10)

        # En az bir kod hucresinde cikti olmali
        has_outputs = any(
            len(c.get("outputs", [])) > 0
            for c in nb["cells"]
            if c.get("cell_type") == "code"
        )
        self.assertTrue(has_outputs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
