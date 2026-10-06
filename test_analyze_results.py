"""
Unit Tests for Empirical Stock Characteristics & Strategy Analyzer
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from analyze_results import analyze_all_stocks, generate_analysis_markdown
from strategies.adaptive_regime import AdaptiveRegimeStrategy
from strategies.sma_crossover import SmaCrossoverStrategy


def create_mock_ohlcv(n_bars: int = 150) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=n_bars)
    t = np.arange(n_bars)
    close = 100.0 + t * 0.2 + 5.0 * np.sin(t / 5.0)
    high = close + 1.5
    low = close - 1.5
    open_p = close + 0.1
    vol = np.full(n_bars, 1_000_000.0)

    df = pd.DataFrame(
        {"Open": open_p, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=dates,
    )
    df.attrs["data_coverage"] = {"end_date_observed": True}
    df.attrs["data_provenance"] = {"source": "test_mock"}
    return df


class TestAnalyzeResults(unittest.TestCase):
    @patch("analyze_results.load_stock_data")
    def test_analyze_all_stocks_columns_and_metrics(self, mock_load):
        mock_load.return_value = create_mock_ohlcv(150)

        df_res = analyze_all_stocks(
            strategy=AdaptiveRegimeStrategy(),
            stocks=["AKBNK.IS"],
            use_cache=True,
        )

        expected_columns = [
            "Hisse",
            "B&H Getiri (%)",
            "Yillik Volatilite (%)",
            "Ort ATR (%)",
            "Ort ADX",
            "Trend Gun (%)",
            "Ort Ciro (M TL)",
            "Trades",
            "Win Rate (%)",
            "Net Kar (TL)",
            "Benchmark Fark (TL)",
            "Durum",
            "ATR Kapanis Cikisi",
            "Ortalamaya Donus Cikisi",
            "Kisa Sureli Zararli Islem",
            "Piyasada Gecen Gun (%)",
            "Max DD (%)",
        ]
        for col in expected_columns:
            self.assertIn(col, df_res.columns)

        self.assertEqual(len(df_res), 1)
        self.assertEqual(df_res.iloc[0]["Hisse"], "AKBNK")
        self.assertIn(df_res.iloc[0]["Durum"], ["PASS", "FAIL"])

    @patch("analyze_results.load_stock_data")
    def test_analyze_with_alternate_strategy(self, mock_load):
        mock_load.return_value = create_mock_ohlcv(150)

        df_res = analyze_all_stocks(
            strategy=SmaCrossoverStrategy(fast_period=5, slow_period=20),
            stocks=["TCELL.IS"],
            use_cache=True,
        )

        self.assertEqual(len(df_res), 1)
        self.assertEqual(df_res.iloc[0]["Hisse"], "TCELL")

    def test_generate_analysis_markdown(self):
        df_dummy = pd.DataFrame([{
            "Hisse": "AKBNK",
            "B&H Getiri (%)": 6.8,
            "Yillik Volatilite (%)": 42.0,
            "Ort ATR (%)": 3.56,
            "Ort ADX": 37.0,
            "Trend Gun (%)": 70.5,
            "Ort Ciro (M TL)": 7825.5,
            "Trades": 10,
            "Win Rate (%)": 40.0,
            "Net Kar (TL)": -20181.39,
            "Benchmark Fark (TL)": -104181.39,
            "Durum": "FAIL",
            "ATR Kapanis Cikisi": 3,
            "Ortalamaya Donus Cikisi": 6,
            "Kisa Sureli Zararli Islem": 0,
            "Piyasada Gecen Gun (%)": 55.0,
            "Max DD (%)": 50.68,
        }])
        md = generate_analysis_markdown(df_dummy, "Test_Strategy")
        self.assertIn("AKBNK", md)
        self.assertIn("Test_Strategy", md)
        self.assertIn("FAIL", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
