"""
Unit Test Suite for Performance Metrics Module (Phase 6)
=========================================================
Test senaryolari:
1. Net Profit ve Net Profit % hesaplama dogrulugu
2. Win Rate ve Trade sayimi
3. Profit Factor (sonsuz brut kayipsiz durum dahil)
4. Max Drawdown (miktar, yuzde ve sure)
5. Sharpe ve Sortino oranlari
6. CAGR hesaplamasi
7. Kazanc/Kayip serileri (Streaks)
8. Tek hisse benchmark karsilastirmasi (PASS/FAIL)
9. Portfoy challenge degerlendirmesi (6/6 kurali)
10. Ozet DataFrame ve CSV uretimi
"""

import unittest
import numpy as np
import pandas as pd

from metrics import (
    calculate_metrics,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_cagr,
    calculate_streaks,
    compare_with_benchmark,
    generate_summary_table,
    evaluate_challenge,
    PerformanceMetrics,
)
from backtester import Trade, BacktestResult


class DummyResult:
    """Metrik testleri icin hafif mock BacktestResult."""
    def __init__(
        self,
        ticker="AKBNK.IS",
        initial_capital=100_000.0,
        final_capital=120_000.0,
        trades=None,
        equity_curve=None,
    ):
        self.ticker = ticker
        self.strategy_name = "MockStrategy"
        self.initial_capital = initial_capital
        self.final_capital = final_capital
        self.trades = trades or []
        if equity_curve is None:
            self.equity_curve = pd.Series([initial_capital, final_capital])
        else:
            self.equity_curve = equity_curve


class TestMetrics(unittest.TestCase):

    def test_basic_pnl_and_win_rate(self):
        """Temel kar/zarar ve kazanma orani hesaplamasi."""
        trades = [
            Trade("2025-01-01", 10, "2025-01-02", 12, 1000, 2000.0, 20.0, "signal"),
            Trade("2025-01-03", 12, "2025-01-04", 15, 1000, 3000.0, 25.0, "signal"),
            Trade("2025-01-05", 15, "2025-01-06", 14, 1000, -1000.0, -6.67, "stop_loss"),
            Trade("2025-01-07", 14, "2025-01-08", 14, 1000, 0.0, 0.0, "max_hold"),
        ]
        equity = pd.Series([100_000, 102_000, 105_000, 104_000, 104_000])
        res = DummyResult(final_capital=104_000, trades=trades, equity_curve=equity)

        m = calculate_metrics(res)
        self.assertEqual(m.net_profit, 4000.0)
        self.assertEqual(m.net_profit_pct, 4.0)
        self.assertEqual(m.total_trades, 4)
        self.assertEqual(m.winning_trades, 2)
        self.assertEqual(m.losing_trades, 1)
        self.assertEqual(m.break_even_trades, 1)
        self.assertEqual(m.win_rate, 50.0)

    def test_profit_factor(self):
        """Gross profit / gross loss hesaplamasi."""
        # Kar: 5000 + 3000 = 8000 TL, Zarar: -2000 TL -> PF = 4.0
        trades = [
            Trade("2025-01-01", 10, "2025-01-02", 15, 1000, 5000.0, 50.0, "signal"),
            Trade("2025-01-03", 15, "2025-01-04", 18, 1000, 3000.0, 20.0, "signal"),
            Trade("2025-01-05", 18, "2025-01-06", 16, 1000, -2000.0, -11.1, "stop_loss"),
        ]
        res = DummyResult(trades=trades)
        m = calculate_metrics(res)
        self.assertEqual(m.profit_factor, 4.0)

    def test_profit_factor_no_losses(self):
        """Hic zararli islem yokken profit factor inf olmali."""
        trades = [
            Trade("2025-01-01", 10, "2025-01-02", 15, 1000, 5000.0, 50.0, "signal"),
        ]
        res = DummyResult(trades=trades)
        m = calculate_metrics(res)
        self.assertEqual(m.profit_factor, float("inf"))

    def test_max_drawdown_calculation(self):
        """Max drawdown miktar, yuzde ve sure hesaplama dogrulugu."""
        # Tepe: 120,000 TL. Dip: 90,000 TL -> DD = 30,000 TL (%25)
        curve = pd.Series([100_000, 120_000, 110_000, 90_000, 105_000, 125_000])
        dd_tl, dd_pct, duration = calculate_max_drawdown(curve)

        self.assertEqual(dd_tl, 30_000.0)
        self.assertEqual(dd_pct, 25.0)
        self.assertEqual(duration, 3)  # 110k, 90k, 105k (3 bar suresi)

    def test_sharpe_and_sortino(self):
        """Sharpe ve Sortino oranlarinin hesaplanmasi."""
        # Surekli artis -> pozitif sharpe ve sortino
        returns = pd.Series([100, 102, 105, 104, 108, 112, 115])
        sharpe = calculate_sharpe_ratio(returns)
        sortino = calculate_sortino_ratio(returns)

        self.assertGreater(sharpe, 0)
        self.assertGreater(sortino, 0)

    def test_cagr_calculation(self):
        """Yilliklandirilmis getiri hesaplamasi."""
        # 1 yilda (252 bar) 100k -> 150k (%50 CAGR)
        cagr = calculate_cagr(100_000, 150_000, 252)
        self.assertAlmostEqual(cagr, 50.0, places=1)

    def test_streaks_calculation(self):
        """Ardisik kazanc ve kayip serileri."""
        trades = [
            Trade("", 0, "", 0, 0, 100, 1, ""),
            Trade("", 0, "", 0, 0, 200, 2, ""),
            Trade("", 0, "", 0, 0, 300, 3, ""),  # 3 ardisik kazanc
            Trade("", 0, "", 0, 0, -50, -1, ""),
            Trade("", 0, "", 0, 0, -80, -1, ""), # 2 ardisik kayip
            Trade("", 0, "", 0, 0, 150, 1, ""),
        ]
        max_w, max_l = calculate_streaks(trades)
        self.assertEqual(max_w, 3)
        self.assertEqual(max_l, 2)

    def test_compare_with_benchmark_cases(self):
        """Benchmark karsilastirmasinin farkli senaryolari."""
        # AKBNK benchmark: 184,000 TL
        # 1. Gecer (190,000 TL, 4 trade)
        comp_pass = compare_with_benchmark(190_000, "AKBNK.IS", total_trades=4)
        self.assertTrue(comp_pass["passed"])
        self.assertTrue(comp_pass["fully_passed"])
        self.assertEqual(comp_pass["status"], "PASS")

        # 2. Elenir (Sermaye yetersiz: 170,000 TL)
        comp_fail_cap = compare_with_benchmark(170_000, "AKBNK.IS", total_trades=4)
        self.assertFalse(comp_fail_cap["passed"])
        self.assertFalse(comp_fail_cap["fully_passed"])
        self.assertEqual(comp_fail_cap["status"], "FAIL")

        # 3. Elenir (Sermaye gecer ama trade sayisi < 3)
        comp_fail_trade = compare_with_benchmark(190_000, "AKBNK.IS", total_trades=2)
        self.assertTrue(comp_fail_trade["passed"]) # Sermaye gecti
        self.assertFalse(comp_fail_trade["meets_trade_rule"]) # Trade kurali gecmedi
        self.assertFalse(comp_fail_trade["fully_passed"])
        self.assertEqual(comp_fail_trade["status"], "FAIL")

    def test_evaluate_challenge_all_and_partial(self):
        """Challenge tum portfoy degerlendirmesi (6/6 kurali)."""
        # 6 hisse hepsi basarili senaryo:
        res_pass = {}
        from config import BENCHMARKS, STOCKS
        for ticker in STOCKS:
            bm_final = BENCHMARKS[ticker]["final_capital"]
            # Benchmark'in 10,000 TL ustu sermaye ve 4 trade
            res_pass[ticker] = DummyResult(
                ticker=ticker,
                final_capital=bm_final + 10_000,
                trades=[Trade("", 0, "", 0, 0, 2500, 1, "")] * 4,
            )

        eval_all_pass = evaluate_challenge(res_pass)
        self.assertTrue(eval_all_pass["all_passed"])
        self.assertEqual(eval_all_pass["passed_count"], 6)
        self.assertEqual(eval_all_pass["challenge_status"], "CHALLENGE PASSED")

        # 1 hisse basarisiz olursa genel sonuc FAILED olmali:
        res_pass["AKBNK.IS"] = DummyResult(
            ticker="AKBNK.IS",
            final_capital=100_000, # AKBNK 184k benchmarkin altinda
            trades=[Trade("", 0, "", 0, 0, 0, 0, "")] * 4,
        )
        eval_one_fail = evaluate_challenge(res_pass)
        self.assertFalse(eval_one_fail["all_passed"])
        self.assertEqual(eval_one_fail["passed_count"], 5)
        self.assertEqual(eval_one_fail["challenge_status"], "CHALLENGE FAILED")

    def test_generate_summary_table_structure(self):
        """Ozet tablosunun beklenen kolonlara sahip olmasi."""
        res_map = {
            "AKBNK.IS": DummyResult(ticker="AKBNK.IS", final_capital=120_000),
            "ASELS.IS": DummyResult(ticker="ASELS.IS", final_capital=350_000),
        }
        df = generate_summary_table(res_map)
        self.assertEqual(len(df), 2)
        expected_cols = ["Hisse", "Baslangic (TL)", "Final (TL)", "Net Kar (TL)", "Durum", "Trades", "Win Rate (%)"]
        for col in expected_cols:
            self.assertIn(col, df.columns)

    @staticmethod
    def passing_results():
        from config import BENCHMARKS, STOCKS
        return {
            ticker: DummyResult(
                ticker=ticker,
                final_capital=BENCHMARKS[ticker]["final_capital"] + 10_000,
                trades=[Trade("2025-01-01", 100, "2025-01-02", 110, 100, 1000, 10, "signal")] * 3,
            )
            for ticker in STOCKS
        }

    def test_zero_trades_cannot_pass_even_with_cash_above_benchmark(self):
        for count in (0, 1, 2):
            with self.subTest(trades=count):
                result = compare_with_benchmark(100_000, "TCELL.IS", total_trades=count)
                self.assertTrue(result["passed"])
                self.assertFalse(result["meets_trade_rule"])
                self.assertFalse(result["fully_passed"])
                self.assertEqual(result["status"], "FAIL")
        self.assertFalse(compare_with_benchmark(100_000, "TCELL.IS")["fully_passed"])

    def test_unknown_ticker_has_no_implicitly_zero_benchmark(self):
        result = compare_with_benchmark(1_000_000, "UNKNOWN.IS", total_trades=3)
        self.assertFalse(result["passed"])
        self.assertFalse(result["fully_passed"])
        self.assertEqual(result["status"], "FAIL")

    def test_incomplete_data_prevents_final_challenge_pass(self):
        results = self.passing_results()
        results["ASELS.IS"].df = pd.DataFrame()
        results["ASELS.IS"].df.attrs["data_coverage"] = {"end_date_observed": False}
        evaluation = evaluate_challenge(results)
        self.assertTrue(evaluation["performance_all_passed"])
        self.assertEqual(evaluation["passed_count"], 6)
        self.assertFalse(evaluation["all_passed"])
        self.assertEqual(evaluation["incomplete_data"], ["ASELS.IS"])
        self.assertIn("PROVISIONAL", evaluation["challenge_status"])
        # Observing the missing final date removes the provisional restriction.
        results["ASELS.IS"].df.attrs["data_coverage"]["end_date_observed"] = True
        self.assertTrue(evaluate_challenge(results)["all_passed"])

    def test_wrong_dictionary_key_identity_cannot_count_as_required_stock(self):
        results = self.passing_results()
        # A profitable duplicate FROTO result must not masquerade as EREGL.
        results["EREGL.IS"] = results["FROTO.IS"]
        evaluation = evaluate_challenge(results)
        self.assertTrue(evaluation["required_stocks_present"])
        self.assertEqual(evaluation["passed_count"], 6)
        self.assertFalse(evaluation["performance_all_passed"])
        self.assertFalse(evaluation["all_passed"])

    def test_six_entries_must_include_all_required_stock_symbols(self):
        results = self.passing_results()
        results["EXTRA.IS"] = results.pop("AKBNK.IS")
        evaluation = evaluate_challenge(results)
        self.assertEqual(evaluation["total_count"], 6)
        self.assertFalse(evaluation["required_stocks_present"])
        self.assertFalse(evaluation["all_passed"])

    def test_empty_results_do_not_vacuously_pass_challenge(self):
        evaluation = evaluate_challenge({})
        self.assertFalse(evaluation["required_stocks_present"])
        self.assertFalse(evaluation["performance_all_passed"])
        self.assertFalse(evaluation["all_passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
