from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class Trade:
    symbol: str
    action: str
    index: int
    price: float


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    final_cash: float
    shares_held: int
    portfolio_value: float
    trades: List[Trade]



def moving_average(values: Sequence[float], window: int, index: int) -> float:
    if window <= 0:
        raise ValueError("window must be positive")
    if index + 1 < window:
        raise ValueError("not enough data points for requested window")
    start = index + 1 - window
    return sum(values[start : index + 1]) / window



def backtest_symbol(
    symbol: str,
    prices: Sequence[float],
    short_window: int = 3,
    long_window: int = 5,
    initial_cash: float = 10_000.0,
) -> BacktestResult:
    if not prices:
        raise ValueError("prices must not be empty")
    if short_window >= long_window:
        raise ValueError("short_window must be less than long_window")
    if long_window > len(prices):
        raise ValueError("long_window cannot be larger than price history")

    cash = initial_cash
    shares = 0
    trades: List[Trade] = []

    for i in range(long_window - 1, len(prices)):
        short_ma = moving_average(prices, short_window, i)
        long_ma = moving_average(prices, long_window, i)
        price = prices[i]

        if short_ma > long_ma and shares == 0:
            buy_size = int(cash // price)
            if buy_size > 0:
                cash -= buy_size * price
                shares += buy_size
                trades.append(Trade(symbol=symbol, action="BUY", index=i, price=price))
        elif short_ma < long_ma and shares > 0:
            cash += shares * price
            shares = 0
            trades.append(Trade(symbol=symbol, action="SELL", index=i, price=price))

    portfolio_value = cash + shares * prices[-1]
    return BacktestResult(
        symbol=symbol,
        final_cash=round(cash, 2),
        shares_held=shares,
        portfolio_value=round(portfolio_value, 2),
        trades=trades,
    )



def backtest_multiple_symbols(
    historical_prices: Dict[str, Sequence[float]],
    short_window: int = 3,
    long_window: int = 5,
    initial_cash_per_symbol: float = 10_000.0,
) -> Dict[str, BacktestResult]:
    results: Dict[str, BacktestResult] = {}
    for symbol, prices in historical_prices.items():
        results[symbol] = backtest_symbol(
            symbol=symbol,
            prices=prices,
            short_window=short_window,
            long_window=long_window,
            initial_cash=initial_cash_per_symbol,
        )
    return results
