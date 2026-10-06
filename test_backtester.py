"""
Unit Test Suite for Backtester Module (Phase 5)
================================================
Test senaryolari:
1. Trade ve BacktestResult veri yapilari ve metodlari
2. Next Open emir gerceklesme mekanizmasi (No Look-Ahead)
3. Same Close emir gerceklesme mekanizmasi
4. Stop-Loss tetiklenme dogrulugu
5. Trailing Stop tetiklenme dogrulugu
6. Max Holding Period tetiklenme dogrulugu
7. End of Data zorla cikis dogrulugu
8. Komisyon ve Slippage hesaplama dogrulugu
9. Sermaye ve Nakit korunumu (Cash conservation)
10. Benchmark karsilastirma dogrulugu
"""

import sys
import unittest
import numpy as np
import pandas as pd

from backtester import Backtester, Trade, BacktestResult
from risk_manager import RiskManager
from strategy_base import StrategyBase


class MockStrategy(StrategyBase):
    """Testler icin onceden tanimlanmis sinyaller ureten sahte strateji."""
    def __init__(self, signals: list[int]):
        super().__init__(name="MockStrategy")
        self.signals = signals

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Signal"] = self.signals[:len(df)]
        return df


def create_dummy_df(
    prices: list[tuple[float, float, float, float]], # Open, High, Low, Close
    dates: list[str] | None = None,
) -> pd.DataFrame:
    """Test icin sentetik OHLCV DataFrame olusturur."""
    n = len(prices)
    if dates is None:
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
    else:
        dates = pd.to_datetime(dates)

    data = {
        "Open": [p[0] for p in prices],
        "High": [p[1] for p in prices],
        "Low": [p[2] for p in prices],
        "Close": [p[3] for p in prices],
        "Volume": [100_000] * n,
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = "Date"
    return df


class TestBacktester(unittest.TestCase):

    def test_trade_properties(self):
        """Trade nesnesi ozellik ve metodlarinin dogrulugu."""
        trade_win = Trade(
            entry_date="2025-01-01", entry_price=10.0,
            exit_date="2025-01-05", exit_price=12.0,
            shares=1000, pnl=2000.0, pnl_pct=20.0,
            exit_reason="signal", ticker="AKBNK.IS"
        )
        self.assertTrue(trade_win.is_winner)
        self.assertFalse(trade_win.is_loser)
        self.assertAlmostEqual(trade_win.return_rate, 0.20)

        trade_loss = Trade(
            entry_date="2025-01-01", entry_price=10.0,
            exit_date="2025-01-05", exit_price=9.0,
            shares=1000, pnl=-1000.0, pnl_pct=-10.0,
            exit_reason="stop_loss", ticker="AKBNK.IS"
        )
        self.assertFalse(trade_loss.is_winner)
        self.assertTrue(trade_loss.is_loser)
        d = trade_loss.to_dict()
        self.assertEqual(d["exit_reason"], "stop_loss")
        self.assertEqual(d["pnl"], -1000.0)

    def test_next_open_execution_no_lookahead(self):
        """
        Sinyal bar 0 Kapanisinda olusur.
        Islem bar 1 Acilisinda gerceklesmelidir.
        """
        # 3 bar:
        # Bar 0: Signal = 1 (BUY) -> Gunun kapanisinda
        # Bar 1: Open=100, High=105, Low=99, Close=104 -> ALIS BURADA OLMALI @ 100
        # Bar 2: Signal = -1 (SELL) -> Gunun kapanisinda
        # Bar 3: Open=110, High=112, Low=108, Close=110 -> SATIS BURADA OLMALI @ 110
        prices = [
            (95, 100, 94, 98),    # Bar 0: BUY sinyali
            (100, 105, 99, 104),  # Bar 1: Giris @ 100
            (103, 108, 102, 107), # Bar 2: SELL sinyali
            (110, 112, 108, 110), # Bar 3: Cikis @ 110
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, -1, 0]

        bt = Backtester(initial_capital=100_000, execution_mode="next_open")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        # Giris Bar 1'in acilisi olmali (100)
        self.assertEqual(t.entry_date, df.index[1])
        self.assertEqual(t.entry_price, 100.0)
        # Cikis Bar 3'un acilisi olmali (110)
        self.assertEqual(t.exit_date, df.index[3])
        self.assertEqual(t.exit_price, 110.0)
        # Lot: 100,000 / 100 = 1000 lot
        self.assertEqual(t.shares, 1000)
        # PnL: 1000 * (110 - 100) = 10,000 TL
        self.assertEqual(t.pnl, 10_000.0)
        self.assertEqual(t.exit_reason, "signal")
        self.assertEqual(res.final_capital, 110_000.0)

    def test_same_close_execution(self):
        """
        Same Close modunda islem sinyal barinin kapanisinda gerceklesmeli.
        """
        prices = [
            (95, 100, 94, 98),    # Bar 0: BUY sinyali -> Giris @ 98
            (100, 105, 99, 104),  # Bar 1: SELL sinyali -> Cikis @ 104
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, -1]

        bt = Backtester(initial_capital=98_000, execution_mode="same_close")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        self.assertEqual(t.entry_date, df.index[0])
        self.assertEqual(t.entry_price, 98.0)
        self.assertEqual(t.exit_date, df.index[1])
        self.assertEqual(t.exit_price, 104.0)
        self.assertEqual(t.shares, 1000)
        self.assertEqual(t.pnl, 6000.0)

    def test_stop_loss_trigger(self):
        """%5 Stop-loss tetiklenmesi ve zararin sinirlanmasi."""
        # Bar 0: Signal=1
        # Bar 1: Open=100 (Giris @ 100). High=101, Low=97, Close=98.
        # Bar 2: Open=98, High=98, Low=94, Close=94. Low=94 <= 95 (stop seviyesi)
        prices = [
            (90, 95, 89, 92),
            (100, 101, 97, 98),
            (98, 98, 94, 94),
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, 0]

        rm = RiskManager(stop_loss_pct=0.05)
        bt = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        self.assertEqual(t.exit_reason, "stop_loss")
        self.assertEqual(t.exit_price, 95.0)  # Stop fiyati 100 * 0.95 = 95
        self.assertEqual(t.shares, 1000)
        self.assertEqual(t.pnl, -5000.0)
        self.assertEqual(res.final_capital, 95_000.0)

    def test_trailing_stop_trigger(self):
        """Trailing stop: Fiyat 100'den 120'ye cikip %3 duserse kar kilitlenmeli."""
        # Bar 0: Signal=1
        # Bar 1: Open=100 (Giris @ 100), High=110, Low=100, Close=110
        # Bar 2: Open=110, High=120, Low=115, Close=120 (Peak=120)
        # Bar 3: Open=120, High=120, Low=115, Close=115. Stop: 120 * 0.97 = 116.4. Low 115 <= 116.4
        prices = [
            (90, 95, 90, 92),
            (100, 110, 100, 110),
            (110, 120, 115, 120),
            (120, 120, 115, 115),
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, 0, 0]

        rm = RiskManager(trailing_stop_pct=0.03)
        bt = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        self.assertEqual(t.exit_reason, "trailing_stop")
        self.assertAlmostEqual(t.exit_price, 116.4, places=2)
        self.assertGreater(t.pnl, 16_000.0)
        self.assertTrue(t.is_winner)

    def test_max_holding_period(self):
        """Max holding period dolunca pozisyondan cikilmali."""
        # Bar 0: Signal=1
        # Bar 1: Giris @ 100 (days_held=0)
        # Bar 2: days_held=1
        # Bar 3: days_held=2 -> Max hold 2 ise Bar 3 kapanisinda emir verilir, Bar 4 acilista cikar
        # Bar 4: Open=105 -> Cikis @ 105
        prices = [
            (90, 95, 90, 92),
            (100, 102, 99, 101),
            (101, 103, 100, 102),
            (102, 104, 101, 103),
            (105, 106, 104, 105),
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, 0, 0, 0]

        rm = RiskManager(max_holding_days=2)
        bt = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        self.assertEqual(t.exit_reason, "max_hold")
        self.assertEqual(t.exit_price, 105.0)

    def test_end_of_data_forced_close(self):
        """Backtest sonunda acik pozisyon varsa son bar kapanisinda kapatilmali."""
        prices = [
            (90, 95, 90, 92),
            (100, 105, 99, 104),
            (104, 110, 103, 108), # Son bar, Close=108
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, 0]

        bt = Backtester(initial_capital=100_000, close_at_end=True, execution_mode="next_open")
        res = bt.run(df, ticker="TEST.IS")

        self.assertEqual(res.total_trades, 1)
        t = res.trades[0]
        self.assertEqual(t.exit_reason, "end_of_data")
        self.assertEqual(t.exit_price, 108.0)
        self.assertEqual(res.final_capital, 108_000.0)

    def test_commission_and_slippage(self):
        """Komisyon ve slippage kesintilerinin dogrulugu."""
        # 100 TL acilis, %1 slippage -> alis 101 TL
        # Komisyon %0.1
        prices = [
            (90, 95, 90, 92),
            (100, 105, 99, 104), # Giris
            (104, 108, 102, 106),
            (110, 112, 108, 110), # Cikis
        ]
        df = create_dummy_df(prices)
        df["Signal"] = [1, 0, -1, 0]

        bt = Backtester(
            initial_capital=100_000,
            commission_rate=0.001, # Binde 1
            slippage_rate=0.005,   # Binde 5
            execution_mode="next_open"
        )
        res = bt.run(df, ticker="TEST.IS")

        t = res.trades[0]
        # Alis: 100 * 1.005 = 100.50
        self.assertAlmostEqual(t.entry_price, 100.5, places=2)
        # Satis: 110 * 0.995 = 109.45
        self.assertAlmostEqual(t.exit_price, 109.45, places=2)
        self.assertGreater(t.commission, 0)
        # Final capital initial'dan buyuk ama masraflar dusulmus
        self.assertAlmostEqual(res.final_capital, res.equity_curve.iloc[-1], places=2)

    def test_benchmark_comparison(self):
        """Benchmark karsilastirmasinin PASS/FAIL dogrulugu."""
        from config import BENCHMARKS
        # AKBNK benchmark final capital = 184,000 TL
        prices = [(100, 105, 95, 100)] * 5
        df = create_dummy_df(prices)
        df["Signal"] = [0] * 5

        # Sermaye benchmarkin altinda
        res_fail = BacktestResult(
            ticker="AKBNK.IS", strategy_name="Test",
            initial_capital=100_000, final_capital=150_000,
            total_net_profit=50_000, total_net_profit_pct=50.0,
            trades=[Trade("2025-01-01", 10, "2025-01-02", 11, 100, 100, 10, "signal")] * 3,
            equity_curve=pd.Series([150_000]), df=df
        )
        comp_fail = res_fail.compare_with_benchmark()
        self.assertFalse(comp_fail["passed"])

        # Sermaye benchmarkin ustunde
        res_pass = BacktestResult(
            ticker="AKBNK.IS", strategy_name="Test",
            initial_capital=100_000, final_capital=190_000,
            total_net_profit=90_000, total_net_profit_pct=90.0,
            trades=[Trade("2025-01-01", 10, "2025-01-02", 11, 100, 100, 10, "signal")] * 3,
            equity_curve=pd.Series([190_000]), df=df
        )
        comp_pass = res_pass.compare_with_benchmark()
        self.assertTrue(comp_pass["passed"])
        self.assertTrue(comp_pass["fully_passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
