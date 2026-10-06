"""
Script to generate and pre-execute main_notebook.ipynb for BIST Challenge
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path


def create_and_execute_notebook():
    nb = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.13.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    # Context dictionary for executing cells sequentially
    global_env = {}

    def md_cell(source):
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in source.split("\n")]
        }

    exec_counter = [1]

    def code_cell(source, execute=True):
        cell_dict = {
            "cell_type": "code",
            "execution_count": exec_counter[0] if execute else None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in source.split("\n")]
        }

        if execute:
            buffer = io.StringIO()
            try:
                with redirect_stdout(buffer):
                    # Mock display for standalone execution
                    global_env["display"] = lambda obj: print(obj)
                    exec(source, global_env)
                captured = buffer.getvalue()
                if captured:
                    cell_dict["outputs"].append({
                        "name": "stdout",
                        "output_type": "stream",
                        "text": [line + "\n" for line in captured.splitlines()]
                    })
            except Exception as e:
                print(f"[!] Cell execution warning: {e}")
            exec_counter[0] += 1

        return cell_dict

    # Cell 1: Title & Overview
    nb["cells"].append(md_cell("""# BIST Algorithmic Trading Challenge
## Python Backtesting & Algorithmic Strategy Implementation

**Ders:** BIST Algorithmic Trading  
**Periyot:** 1 Ocak 2025 - 1 Ekim 2026  
**Baslangic Sermayesi:** Hisse basina 100,000 TL  
**Kapsanan Hisseler:** AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL  

---

### Proje Kurallari ve Benchmark Hedefleri

| Hisse | Baslangic Sermaye | Benchmark Net Kar | Benchmark Final Sermaye |
|:---|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | +84,000 TL | 184,000 TL |
| **ASELS** | 100,000 TL | +239,000 TL | 339,000 TL |
| **TUPRS** | 100,000 TL | +72,000 TL | 172,000 TL |
| **TCELL** | 100,000 TL | -18,000 TL | 82,000 TL |
| **FROTO** | 100,000 TL | +3,000 TL | 103,000 TL |
| **EREGL** | 100,000 TL | +39,000 TL | 139,000 TL |

> **Zorunlu Kurallar:**
> 1. Ayni temel strateji 6 hissenin tamamina uygulanmalidir.
> 2. Toplam portfoy kari tek basina yeterli degildir; **her hisse kendi benchmark'ini bireysel olarak gecmelidir**.
> 3. Her hisse icin en az **3 tamamlanmis islem** uretilmelidir.
> 4. **No Look-Ahead Kurali:** Sadece o ana kadar olan veri kullanilabilir.
> 5. **Risk Yonetimi Zorunlulugu:** Stop-loss, trailing stop, ATR stop veya position sizing mekanizmasi icermelidir.
"""))

    # Cell 2: Setup & Imports
    nb["cells"].append(md_cell("""## 1. Kütüphaneler ve Modüllerin Yüklenmesi"""))
    nb["cells"].append(code_cell("""import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Proje kok dizini
sys.path.insert(0, os.path.abspath("."))

from config import STOCKS, INITIAL_CAPITAL, BENCHMARKS, get_short_name, get_benchmark
from data_loader import load_stock_data, load_all_stocks
from indicators import add_sma, add_ema, add_rsi, add_atr, add_macd
from strategy_base import StrategyBase
from risk_manager import RiskManager
from backtester import Backtester, Trade, BacktestResult
from metrics import calculate_metrics, evaluate_challenge, generate_summary_table, print_metrics_summary
from visualizer import plot_stock_dashboard, plot_benchmark_comparison, plot_all_equity_curves, plot_all_dashboards
from runner import run_pipeline

print("[OK] Tum moduller basariyla import edildi.")
print(f"Hisseler: {', '.join([get_short_name(s) for s in STOCKS])}")"""))

    # Cell 3: Data Inspection
    nb["cells"].append(md_cell("""## 2. BIST Hisse Verilerinin Yüklenmesi ve İncelenmesi
Her hisse için 2025-01-01 ile 2026-10-01 tarihleri arasındaki günlük OHLCV verileri yüklenir."""))
    nb["cells"].append(code_cell("""# Verileri yukle ve ozet tablosunu olustur
data_summary = []
all_data = {}

for ticker in STOCKS:
    df = load_stock_data(ticker, use_cache=True)
    all_data[ticker] = df
    short = get_short_name(ticker)
    data_summary.append({
        "Hisse": short,
        "Ticker": ticker,
        "Gun Sayisi": len(df),
        "Baslangic": df.index[0].strftime("%Y-%m-%d"),
        "Bitis": df.index[-1].strftime("%Y-%m-%d"),
        "Ilk Fiyat (TL)": round(df["Close"].iloc[0], 2),
        "Son Fiyat (TL)": round(df["Close"].iloc[-1], 2),
        "Getiri (%)": round(((df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1) * 100, 2),
    })

df_data_summary = pd.DataFrame(data_summary)
print(df_data_summary.to_string(index=False))"""))

    # Cell 4: Strategy Definition
    nb["cells"].append(md_cell("""## 3. Strateji Mimarisi (StrategyBase) ve Sinyal Üretimi
Strateji nesnemiz `StrategyBase` sınıfından türetilmiştir. Sadece o ana kadar olan verileri kullanarak `Signal` kolonu üretir:
- `1`: BUY (Alış)
- `-1`: SELL (Satış)
- `0`: HOLD (Bekle)"""))
    nb["cells"].append(code_cell("""from strategies.sma_crossover import SmaCrossoverStrategy

# Strateji ornegi: SMA Crossover (Fast=10, Slow=50)
strategy = SmaCrossoverStrategy(fast_period=10, slow_period=50)
print(f"Secilen Strateji: {strategy}")

# Ornek olarak AKBNK uzerinde uretilen sinyaller
df_sample = strategy.run(all_data["AKBNK.IS"])
print("\\nSinyal Dagilimi (AKBNK):")
print(df_sample["Signal"].value_counts())"""))

    # Cell 5: Risk Management
    nb["cells"].append(md_cell("""## 4. Risk Yönetimi (RiskManager)
Şartnameye uygun olarak stratejiden bağımsız risk yönetimi mekanizmaları tanımlanır:
- **Stop-Loss:** %5 sabit kayıp koruması
- **Trailing Stop:** %3 zirveden geri çekilmede kârı kilitleme
- **Position Sizing:** Sermaye korumalı lot hesabı"""))
    nb["cells"].append(code_cell("""# Risk Yoneticisi Tanimlama
rm = RiskManager(
    stop_loss_pct=0.05,       # %5 Stop-Loss
    trailing_stop_pct=0.03,   # %3 Trailing Stop
    max_holding_days=None,    # Istege bagli maksimum bar suresi
    position_size_pct=1.0,    # Tum nakit ile pozisyon boyutlama
)

print(f"Aktif Risk Mekanizmalari: {rm.get_active_mechanisms()}")"""))

    # Cell 6: Running the Backtest
    nb["cells"].append(md_cell("""## 5. End-to-End Backtest Simülasyonu
Tüm 6 hisse üzerinde `run_pipeline` çalıştırılarak emirler (No Look-Ahead garantili `next_open` modunda) yürütülür."""))
    nb["cells"].append(code_cell("""# Pipeline calistir (Tum hisseler + risk yonetimi + metrikler + grafikler)
results, challenge_eval, df_summary = run_pipeline(
    strategy=strategy,
    risk_manager=rm,
    execution_mode="next_open",
    save_charts=True,
    save_trades=True,
    save_metrics=True,
    print_summary=True,
)"""))

    # Cell 7: Detailed Trade Logs
    nb["cells"].append(md_cell("""## 6. Tamamlanmış İşlem Logları (Trade Details)
Şartname gereği her hisse için gerçekleştirilen tüm işlemler (alış/satış tarihleri, fiyatlar, lot sayısı, PnL ve çıkış sebepleri) aşağıda listelenmiştir."""))
    nb["cells"].append(code_cell("""# Her hissenin trade tablosunu goster
for ticker, res in results.items():
    short = get_short_name(ticker)
    print(f"\\n{'='*75}\\n{short} ISLEM GECMISI ({res.total_trades} Islem)\\n{'='*75}")
    df_t = res.trades_df
    if not df_t.empty:
        cols = ["entry_date", "entry_price", "exit_date", "exit_price", "shares", "pnl", "pnl_pct", "exit_reason", "bars_held", "cum_capital"]
        print(df_t[cols].to_string(index=False))
    else:
        print("Hic islem uretilmedi.")"""))

    # Cell 8: Metrics and Benchmark Comparison
    nb["cells"].append(md_cell("""## 7. Performans Metrikleri ve Benchmark Karşılaştırması
Tüm 6 hissenin şartnamedeki metrikleri ve bireysel benchmark hedeflerine göre durumu:"""))
    nb["cells"].append(code_cell("""# Ozet karsilastirma tablosu
print(df_summary.to_string(index=False))

print(f"\\nGenel Portfoy Net Kari : {challenge_eval['total_net_profit']:+,.2f} TL ({challenge_eval['total_net_profit_pct']:+.2f}%)")
print(f"Gecen Hisseler          : {', '.join(challenge_eval['passed_stocks']) if challenge_eval['passed_stocks'] else 'Yok'}")
print(f"Kalan Hisseler          : {', '.join(challenge_eval['failed_stocks'])}")
print(f"BIST Challenge Durumu   : {challenge_eval['challenge_status']} [{challenge_eval['passed_count']}/{challenge_eval['total_count']}]")"""))

    # Cell 9: Visualizations
    nb["cells"].append(md_cell("""## 8. Görselleştirmeler ve Grafikler
Her hissenin 3-in-1 paneli (Fiyat + Emirler, Equity Curve + Benchmark, PnL Barları) ve portföy karşılaştırma grafikleri `results/charts/` dizininde üretilmiştir."""))
    nb["cells"].append(code_cell("""# Grafik dosyalarini listele
charts = list(Path("results/charts").glob("*.png"))
print(f"Uretilen Grafik Sayisi: {len(charts)}")
for c in sorted(charts):
    print(f"  - {c.name} ({c.stat().st_size / 1024:.1f} KB)")"""))

    # Cell 10: Conclusion & Extensibility
    nb["cells"].append(md_cell("""## 9. Yeni Strateji Ekleme ve Test Etme Rehberi
Proje mimarisi tam modüler tasarlanmıştır. Yeni bir algoritma denemek için sadece şu adımları izleyin:

```python
# 1. strategies/altina yeni_strateji.py olustur:
from strategy_base import StrategyBase
from indicators import add_rsi, add_bollinger_bands

class MyCustomStrategy(StrategyBase):
    def generate_signals(self, df):
        df["Signal"] = 0
        # ... sinyal kurallarini yaz ...
        return df

# 2. runner.py veya bu notebook'ta calistir:
my_strat = MyCustomStrategy()
results, eval_res, df_sum = run_pipeline(my_strat, rm)
```

Hiçbir zaman backtester, metrics, visualizer veya data loader modüllerini değiştirmeniz gerekmez!
"""))

    output_path = Path("main_notebook.ipynb")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)

    print(f"[OK] Notebook basariyla olusturuldu ve ciktilari eklendi: {output_path.resolve()}")


if __name__ == "__main__":
    create_and_execute_notebook()
