import unittest

from trading_bot import backtest_multiple_symbols, backtest_symbol


class TradingBotTests(unittest.TestCase):
    def test_buy_and_sell_with_crossovers(self):
        prices = [10, 10, 10, 11, 12, 10, 9]
        result = backtest_symbol("SISE", prices, short_window=2, long_window=3, initial_cash=100)

        self.assertEqual([t.action for t in result.trades], ["BUY", "SELL"])
        self.assertGreaterEqual(result.final_cash, 0)
        self.assertEqual(result.shares_held, 0)

    def test_multiple_symbols_backtest(self):
        historical = {
            "THYAO": [100, 101, 102, 104, 103, 101, 99],
            "KCHOL": [50, 49, 48, 49, 50, 52, 54],
        }
        results = backtest_multiple_symbols(historical, short_window=2, long_window=3, initial_cash_per_symbol=1000)

        self.assertEqual(set(results.keys()), {"THYAO", "KCHOL"})
        self.assertTrue(all(r.portfolio_value > 0 for r in results.values()))

    def test_validation(self):
        with self.assertRaises(ValueError):
            backtest_symbol("BIMAS", [], short_window=2, long_window=3)


if __name__ == "__main__":
    unittest.main()
