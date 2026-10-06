# BIST Algorithmic Trading Challenge
## Python Backtesting & Algorithmic Trading System

BIST 100 endeksinin lokomotif 6 hissesi (**AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL**) için geliştirilmiş, tam modüler, **No Look-Ahead** garantili algoritmik alım-satım ve backtest sistemi.

---

## 📌 Proje Kapsamı ve Kurallar

- **Periyot:** 1 Ocak 2025 - 1 Ekim 2026 (440 İşlem Günü)
- **Başlangıç Sermayesi:** Hisse başına 100,000 TL (Toplam 600,000 TL)
- **Kural 1:** Aynı temel strateji 6 hissenin tamamına uygulanır.
- **Kural 2:** Her hisse kendi benchmark hedefini bireysel olarak geçmelidir (**Individual Stock Benchmark Rule**).
- **Kural 3:** Her hisse için en az **3 tamamlanmış işlem** üretilmelidir.
- **Kural 4 (No Look-Ahead):** Sadece işlem anında mevcut veriler kullanılır.
- **Kural 5 (Risk Yönetimi):** Stop-loss, trailing stop, ATR stop veya position sizing mekanizması zorunludur.

---

## 🎯 Benchmark Hedefleri

| Hisse | Başlangıç Sermaye | Benchmark Net Kâr | Benchmark Final Sermaye |
|:---|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | +84,000 TL | 184,000 TL |
| **ASELS** | 100,000 TL | +239,000 TL | 339,000 TL |
| **TUPRS** | 100,000 TL | +72,000 TL | 172,000 TL |
| **TCELL** | 100,000 TL | -18,000 TL | 82,000 TL |
| **FROTO** | 100,000 TL | +3,000 TL | 103,000 TL |
| **EREGL** | 100,000 TL | +39,000 TL | 139,000 TL |

---

## 🏗️ Proje Mimarisi

```
econ_bist_stock/
├── config.py                  # Sabitler, hisse listesi, benchmark hedefleri, yollar
├── data_loader.py             # yfinance veri çekici, cache ve veri doğrulama
├── indicators.py              # Trend, momentum, volatilite indikatör kütüphanesi
├── strategy_base.py           # Tüm stratejilerin türediği Abstract Base Class
├── risk_manager.py            # Stop-loss, trailing stop, ATR stop, position sizing
├── backtester.py              # No Look-Ahead backtest motoru (Trade & BacktestResult)
├── metrics.py                 # Zorunlu metrikler, risk oranları, PASS/FAIL analizi
├── visualizer.py              # 3-in-1 paneller, benchmark barları, portföy grafikleri
├── runner.py                  # End-to-end CLI & pipeline çalıştırıcı
├── analysis_report.md         # Phase 9 Final Analiz Raporu
├── main_notebook.ipynb        # Ödev teslim Jupyter Notebook'u (çıktılar hazır)
├── build_notebook.py          # Notebook derleyici ve otomatik çalıştırıcı
├── analyze_results.py         # Ampirik hisse karakteristiği analiz scripti
├── data/                      # Önbelleğe alınmış OHLCV CSV verileri
├── results/
│   ├── charts/                # 8 adet yüksek çözünürlüklü PNG grafik
│   ├── trades/                # Her hissenin detaylı trade log CSV dosyaları
│   ├── metrics_summary.csv    # Özet metrikler tablosu
│   └── metrics_report.md      # Otomatik oluşturulan markdown rapor
└── test_*.py                  # 28 adet otomatik Unit Test
```

---

## ⚡ Hızlı Başlangıç

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Testleri Çalıştırın (28 Unit Test)
```bash
python -m unittest discover -s . -p "test_*.py"
```

### 3. Backtest Pipeline'ını Çalıştırın
```bash
# Varsayılan parametrelerle:
python runner.py

# Özel parametrelerle:
python runner.py --fast 10 --slow 50 --stop-loss 0.05 --trailing-stop 0.03
```

### 4. Jupyter Notebook'u İnceleyin
[`main_notebook.ipynb`](main_notebook.ipynb) dosyasını VS Code veya Jupyter Lab'de açabilirsiniz. Tüm çıktılar ve grafikler önceden çalıştırılmış ve görünür durumdadır.

---

## 💡 Yeni Strateji Ekleme Rehberi

Proje tam modüler tasarlanmıştır. Yeni bir algoritma eklemek için:

```python
# 1. strategies/yeni_strateji.py oluşturun:
from strategy_base import StrategyBase
from indicators import add_rsi, add_bollinger_bands

class MyStrategy(StrategyBase):
    def generate_signals(self, df):
        df["Signal"] = 0
        # Alış sinyalleri için df.loc[..., "Signal"] = 1
        # Satış sinyalleri için df.loc[..., "Signal"] = -1
        return df

# 2. runner.py veya notebook'ta çalıştırın:
from runner import run_pipeline
from risk_manager import RiskManager

strategy = MyStrategy()
rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
results, eval_res, df_summary = run_pipeline(strategy, rm)
```

---

## 📊 İlerleme Durumu

| Phase | Modül / Konu | Durum |
|:---|:---|:---:|
| **Phase 1** | Config + Data Loader | ✅ Tamamlandı |
| **Phase 2** | İndikatör Kütüphanesi | ✅ Tamamlandı |
| **Phase 3** | Strateji Base + Örnek Strateji | ✅ Tamamlandı |
| **Phase 4** | Risk Manager | ✅ Tamamlandı |
| **Phase 5** | Backtest Motoru | ✅ Tamamlandı |
| **Phase 6** | Performans Metrikleri & Benchmark | ✅ Tamamlandı |
| **Phase 7** | Görselleştirme (Paneller & Grafikler) | ✅ Tamamlandı |
| **Phase 8** | Runner & Jupyter Notebook | ✅ Tamamlandı |
| **Phase 9** | Final Analiz Raporu (`analysis_report.md`) | ✅ Tamamlandı |