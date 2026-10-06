# econ_bist_stock

BIST hisseleri için geçmiş fiyat verisi üzerinde çalışan basit bir alım-satım botu (backtest) algoritması içerir.

## Özellik

- Birden fazla hisse için aynı anda backtest
- Basit hareketli ortalama (SMA) kesişimine göre al/sat
- Her hisse için işlem geçmişi ve portföy sonucu

## Kullanım

```python
from trading_bot import backtest_multiple_symbols

historical_prices = {
    "SISE": [45.2, 45.5, 46.0, 46.8, 47.1, 46.3, 45.9],
    "THYAO": [278.0, 279.5, 281.0, 285.0, 282.0, 279.0, 276.0],
}

results = backtest_multiple_symbols(
    historical_prices,
    short_window=2,
    long_window=3,
    initial_cash_per_symbol=10000,
)

for symbol, result in results.items():
    print(symbol, result.portfolio_value, [t.action for t in result.trades])
```

## Test

```bash
python -m unittest discover -s tests
```
