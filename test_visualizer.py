"""
Unit Test Suite for Visualization Module (Phase 7)
===================================================
Test senaryolari:
1. plot_stock_dashboard fonksiyonunun ciktisi ve Figure tipi
2. plot_benchmark_comparison fonksiyonunun ciktisi
3. plot_all_equity_curves fonksiyonunun ciktisi
4. plot_all_dashboards toplu uretim fonksiyonu
5. Hic islem olmayan (0 trade) bos senaryo dayanikliligi
6. Dosya olusturma ve Path dogrulugu
"""

import unittest
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from backtester import Trade, BacktestResult
from visualizer import (
    plot_stock_dashboard,
    plot_benchmark_comparison,
    plot_all_equity_curves,
    plot_all_dashboards,
)


class TestVisualizer(unittest.TestCase):

    def setUp(self):
        # Sentetik DataFrame ve Trade verisi
        dates = pd.date_range("2025-01-01", periods=20, freq="D")
        self.df = pd.DataFrame({
            "Open": [100 + i for i in range(20)],
            "High": [105 + i for i in range(20)],
            "Low": [98 + i for i in range(20)],
            "Close": [102 + i for i in range(20)],
            "Volume": [1000] * 20,
            "SMA_10": [100.0] * 20,
        }, index=dates)

        self.trades = [
            Trade(dates[1], 101.0, dates[5], 107.0, 1000, 6000.0, 6.0, "signal", "AKBNK.IS", 4, 10.0, 106000.0),
            Trade(dates[8], 109.0, dates[12], 105.0, 1000, -4000.0, -3.7, "stop_loss", "AKBNK.IS", 4, 10.0, 102000.0),
            Trade(dates[14], 115.0, dates[18], 120.0, 1000, 5000.0, 4.3, "trailing_stop", "AKBNK.IS", 4, 10.0, 107000.0),
        ]
        self.equity_curve = pd.Series([100000 + i * 500 for i in range(20)], index=dates)

        self.mock_result = BacktestResult(
            ticker="AKBNK.IS",
            strategy_name="TestStrategy",
            initial_capital=100_000.0,
            final_capital=107_000.0,
            total_net_profit=7_000.0,
            total_net_profit_pct=7.0,
            trades=self.trades,
            equity_curve=self.equity_curve,
            df=self.df,
        )

        self.test_dir = Path("results/test_charts")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Temizlik
        if self.test_dir.exists():
            for f in self.test_dir.glob("*.png"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                self.test_dir.rmdir()
            except Exception:
                pass

    def test_plot_stock_dashboard(self):
        """Dashboard uretimi ve PNG dosyasinin olustugunu dogrula."""
        out_file = self.test_dir / "test_akbnk_dashboard.png"
        fig = plot_stock_dashboard(self.mock_result, save_path=out_file)

        self.assertIsInstance(fig, plt.Figure)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 5000)

    def test_plot_stock_dashboard_no_trades(self):
        """0 islem durumunda hata vermeden calismali."""
        empty_res = BacktestResult(
            ticker="AKBNK.IS",
            strategy_name="EmptyStrategy",
            initial_capital=100_000.0,
            final_capital=100_000.0,
            total_net_profit=0.0,
            total_net_profit_pct=0.0,
            trades=[],
            equity_curve=self.equity_curve,
            df=self.df,
        )
        out_file = self.test_dir / "test_empty_dashboard.png"
        fig = plot_stock_dashboard(empty_res, save_path=out_file)

        self.assertIsInstance(fig, plt.Figure)
        self.assertTrue(out_file.exists())

    def test_plot_benchmark_comparison(self):
        """Benchmark bar grafigi uretimi."""
        results = {"AKBNK.IS": self.mock_result}
        out_file = self.test_dir / "test_bm_comp.png"
        fig = plot_benchmark_comparison(results, save_path=out_file)

        self.assertIsInstance(fig, plt.Figure)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 5000)

    def test_plot_all_equity_curves(self):
        """Toplu equity egrileri grafigi uretimi."""
        results = {"AKBNK.IS": self.mock_result}
        out_file = self.test_dir / "test_all_equity.png"
        fig = plot_all_equity_curves(results, save_path=out_file)

        self.assertIsInstance(fig, plt.Figure)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 5000)

    def test_plot_all_dashboards(self):
        """plot_all_dashboards toplu fonksiyonunun tum dosyalari kaydetmesi."""
        results = {"AKBNK.IS": self.mock_result}
        saved = plot_all_dashboards(results, save_dir=self.test_dir)

        self.assertIn("AKBNK_dashboard", saved)
        self.assertIn("benchmark_comparison", saved)
        self.assertIn("all_equity_curves", saved)
        for path in saved.values():
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
