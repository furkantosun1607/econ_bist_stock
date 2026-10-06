# BIST Algorithmic Trading Challenge
## Python Backtesting & Algorithmic Trading System

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Tests](https://img.shields.io/badge/Unit%20Tests-28%2F28%20Passing-success.svg)
![Market](https://img.shields.io/badge/Market-Borsa%20%C4%B0stanbul%20(BIST)-red.svg)
![No Look-Ahead](https://img.shields.io/badge/Simulation-Strict%20No%20Look--Ahead-brightgreen.svg)

Borsa İstanbul'un 6 lokomotif hissesi (**AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL**) üzerinde algoritmik ticaret stratejileri geliştirmek, simüle etmek, risk yönetimi uygulamak ve performans metriklerini hesaplamak üzere inşa edilmiş, modüler ve kurumsal standartlarda bir algoritmik işlem platformudur.

---

## 📌 Proje Kapsamı ve Zorunlu Kurallar

Proje, **BIST Algorithmic Trading Challenge** teknik şartnamesine tam uyumlu olarak tasarlanmıştır:

1. **Tek Birleşik Strateji Kuralı (Core Unified Strategy):**
   > **Aynı temel strateji 6 hissenin tamamına ortak olarak uygulanmalıdır.**  
   > Hisseler için ayrı ayrı özel stratejiler yazmak veya manuel tarihler seçmek yasaktır; tüm alım-satım kararları Python kuralları tarafından üretilmelidir.
2. **Bireysel Benchmark Kuralı (Individual Stock Benchmark Rule):**
   > Toplam portföy kârı tek başına challenge'ı geçmek için yeterli değildir. **Her hisse kendi benchmark nihai sermaye hedefini bireysel olarak geçmelidir.**
3. **Minimum İşlem Sayısı Kuralı:**
   > Her hisse için en az **3 tamamlanmış işlem (completed trade)** üretilmelidir.
4. **No Look-Ahead Garantisi:**
   > Strateji yalnızca işlem anında erişilebilir olan geçmiş ve anlık verileri kullanabilir. Gelecek fiyatları, gelecek getirileri veya sonradan en iyi görünen tarihler kullanılamaz.
5. **Zorunlu Risk Yönetimi:**
   > Strateji en az bir risk yönetimi mekanizması (stop-loss, trailing stop, ATR stop, maksimum pozisyon süresi veya pozisyon boyutlama) içermelidir.
6. **Kararlaştırılan Parametreler & Tercihler:**
   - **Strateji Türü:** Dersteki stratejilerle sınırlı olmayan, 6 hissenin tamamında kârı maksimize edecek özel/hibrit algoritma.
   - **Position Sizing:** **Full Capital (%100)** — Her işlemde mevcut nakdin tamamı bileşik (compounding) olarak kullanılır.
   - **Komisyon & Slippage:** Hesaba katılmaz (`COMMISSION_RATE = 0.0`, `SLIPPAGE_RATE = 0.0`).
   - **Periyot:** 1 Ocak 2025 - 1 Ekim 2026 (440 İşlem Günü).
   - **Başlangıç Sermayesi:** Hisse başına 100,000 TL (Toplam 600,000 TL).

---

## 🎯 Benchmark Hedefleri

Her bir hisse için aşılması gereken minimum hedef sermayeler:

| Hisse | Başlangıç Sermayesi | Benchmark Net Kâr | Benchmark Final Sermaye | Zorunlu Hedef Durumu |
|:---|:---:|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | +84,000 TL | **184,000 TL** | Bireysel Aşılmalı |
| **ASELS** | 100,000 TL | +239,000 TL | **339,000 TL** | Bireysel Aşılmalı |
| **TUPRS** | 100,000 TL | +72,000 TL | **172,000 TL** | Bireysel Aşılmalı |
| **TCELL** | 100,000 TL | -18,000 TL | **82,000 TL** | Bireysel Aşılmalı |
| **FROTO** | 100,000 TL | +3,000 TL | **103,000 TL** | Bireysel Aşılmalı |
| **EREGL** | 100,000 TL | +39,000 TL | **139,000 TL** | Bireysel Aşılmalı |

---

## 🏗️ Modüler Mimari ve Sistem Bileşenleri

Proje, yeni stratejilerin tek bir satır dahi altyapı koduna dokunmadan test edilebilmesi için katmanlı bir yapıda geliştirilmiştir:

```
econ_bist_stock/
│
├── config.py                  # Proje sabitleri, hisse listesi, benchmark hedefleri, yollar
├── data_loader.py             # yfinance otomatik veri çekici, CSV cache ve temizlik
├── indicators.py              # Trend, momentum, volatilite ve hacim indikatörleri kütüphanesi
├── strategy_base.py           # Tüm stratejilerin türediği Abstract Base Class
├── risk_manager.py            # Stop-loss, trailing stop, ATR stop, max holding, full sizing
├── backtester.py              # Gerçekçi, No Look-Ahead emir yürütme motoru
├── metrics.py                 # Zorunlu performans metrikleri, risk oranları, PASS/FAIL analizi
├── visualizer.py              # 3-in-1 detaylı grafik panelleri ve portföy karşılaştırma çizimleri
├── runner.py                  # End-to-end tek komutla çalışan CLI & pipeline yürütücüsü
├── analysis_report.md         # "Aynı strateji neden farklı sonuç verdi?" final analiz raporu
├── main_notebook.ipynb        # Önceden çalıştırılmış çıktılarıyla ödev teslim Jupyter Notebook'u
├── build_notebook.py          # Notebook derleyici ve otomatik çalıştırıcı script
├── analyze_results.py         # Hisselerin ampirik rejim ve volatilite analiz motoru
│
├── data/                      # 6 hissenin yerel önbelleklenmiş OHLCV CSV verileri
│   ├── AKBNK_ohlcv.csv
│   ├── ASELS_ohlcv.csv
│   ├── TUPRS_ohlcv.csv
│   ├── TCELL_ohlcv.csv
│   ├── FROTO_ohlcv.csv
│   └── EREGL_ohlcv.csv
│
├── strategies/                # Strateji sınıfları klasörü (yeni stratejiler buraya eklenir)
│   ├── __init__.py
│   └── sma_crossover.py       # Örnek/test hareketli ortalama kesişim stratejisi
│
├── results/                   # Çıktı ve teslim dosyaları
│   ├── charts/                # 8 adet yüksek çözünürlüklü (150 DPI) PNG grafik
│   ├── trades/                # 6 hissenin her biri için tüm alım-satım logları (CSV)
│   ├── metrics_summary.csv    # Karşılaştırmalı performans metrikleri tablosu
│   └── metrics_report.md      # Otomatik oluşturulan GitHub formatlı performans raporu
│
└── test_*.py                  # 28 adet otomatik Unit Test (Tüm bileşenleri doğrular)
    ├── test_backtester.py     # 9 test (No look-ahead, stoplar, emir yürütme)
    ├── test_metrics.py        # 10 test (Net kar, Sharpe, Sortino, Drawdown, kurallar)
    ├── test_visualizer.py     # 5 test (Grafik üretimi, dosya kaydı)
    └── test_runner.py         # 4 test (Pipeline, CLI, registry, notebook formatı)
```

---

## 🧩 Modüllerin Teknik Detayları

### 1. `config.py` (Yapılandırma)
- Hisse sembolleri (`STOCKS = ['AKBNK.IS', 'ASELS.IS', ...]`).
- Tarih aralığı (`2025-01-01` - `2026-10-01`) ve hisse başına 100,000 TL başlangıç sermayesi.
- Hisse bazlı benchmark hedefleri sözlüğü (`BENCHMARKS`).
- Komisyon ve slippage oranları (`0.0`).

### 2. `data_loader.py` (Veri Yönetimi)
- `yfinance` üzerinden otomatik adjusted verileri çeker.
- `data/` klasörüne CSV olarak önbelleğe alır (çevrimdışı ve hızlı çalışma).
- Eksik verileri, duplicate indeksleri ve negatif fiyatları temizler.

### 3. `indicators.py` (Teknik İndikatör Kütüphanesi)
Harici ağır kütüphanelere bağımlı kalmadan optimize `numpy` ve `pandas` fonksiyonları:
- **Trend:** Basit Hareketli Ortalama (`SMA`), Üstel Hareketli Ortalama (`EMA`), `MACD`, `ADX / DI`.
- **Momentum:** `RSI`, `Momentum`, `CCI`, `Williams %R`.
- **Volatilite:** `ATR` (Average True Range), `Bollinger Bands`.
- **Hacim:** `OBV`, `CMF`, `VWAP`, `Volume SMA`.

### 4. `strategy_base.py` (Strateji Arayüzü)
- Tüm stratejilerin miras aldığı `StrategyBase` sınıfı.
- Tek zorunlu metot: `generate_signals(df) -> df['Signal']` (1: BUY, -1: SELL, 0: HOLD).
- No look-ahead ve geçerli sinyal kontrolü (`_validate_signals`).

### 5. `risk_manager.py` (Risk Yönetimi)
Stratejiden tamamen bağımsız çalışır:
- **Sabit Stop-Loss:** Yüzdesel zarar sınırı (örn: %5).
- **Trailing Stop:** Zirve fiyattan geri çekilme koruması (örn: %3).
- **ATR Stop:** Oynaklığa duyarlı dinamik stop seviyesi (örn: $2.5 \times \text{ATR}$).
- **Maksimum Pozisyon Süresi:** Belirli bar sonra zorunlu çıkış.
- **Position Sizing:** Full capital (%100 nakit) veya risk bazlı lot hesabı.

### 6. `backtester.py` (Backtest Motoru)
- **No Look-Ahead Garantisi:** Bar $t$ kapanışında üretilen sinyal, ertesi günün açılışında (`next_open`) yürütülür. İsteğe bağlı `same_close` desteği.
- **Trade Loglama:** Her işlem için `entry_date`, `entry_price`, `exit_date`, `exit_price`, `shares`, `pnl`, `pnl_pct`, `exit_reason`, `bars_held` kaydı.
- **Mark-to-Market Equity Curve:** Günlük net portföy değeri serisi.

### 7. `metrics.py` (Performans ve Benchmark Analizi)
- **Şartnamedeki Zorunlu Metrikler:** Net Profit, Final Capital, Total Trades, Winning/Losing Trades, Win Rate, Max Drawdown, Profit Factor, Average Trade.
- **Gelişmiş Metrikler:** Sharpe Ratio, Sortino Ratio (semi-variance), Calmar Ratio, CAGR, Payoff Ratio, Max Drawdown Süresi, Kazanç/Kayıp Serileri (Streaks).
- `compare_with_benchmark()` ve `evaluate_challenge()` ile bireysel ve portföy bazlı PASS/FAIL denetimi.

### 8. `visualizer.py` (Görselleştirme)
- **3-in-1 Dashboard:** Fiyat + Alım/Satım Okları (▲/▼) + Kâr/Zarar Aralığı + Equity Curve + Benchmark Çizgisi + Trade PnL Barları + Metrik Bilgi Kutusu.
- **Benchmark Karşılaştırma Grafiği:** 6 hissenin Final Sermaye vs Benchmark Hedeflerini gösteren gruplu bar grafiği.
- **Toplu Equity Eğrileri:** 6 hissenin sermaye değişimini tek çizimde gösteren grafik.

### 9. `runner.py` (Tek Komutla Çalıştırma)
- Veri yükleme, sinyal üretimi, backtest, risk yönetimi, metrik hesabı, grafik üretimi ve CSV/MD raporlamasını birbirine bağlayan CLI motoru.

---

## ⚡ Kurulum ve Çalıştırma

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Test Paketini Doğrulayın (28 Unit Test)
```bash
python -m unittest discover -s . -p "test_*.py"
```
*Tüm testlerin hatasız geçtiğinden (28/28 OK) emin olun.*

### 3. Backtest Pipeline'ını Çalıştırın
```bash
# Standart çalıştırma:
python runner.py

# Özel parametrelerle çalıştırma:
python runner.py --fast 10 --slow 50 --stop-loss 0.05 --trailing-stop 0.03 --mode next_open
```

### 4. Teslim Jupyter Notebook'unu İnceleyin
Ödev teslimi için hazırlanan [`main_notebook.ipynb`](main_notebook.ipynb) dosyasını VS Code veya Jupyter Lab ile açabilirsiniz. Tüm kod hücreleri ve konsol/tablo/grafik çıktıları **önceden çalıştırılmış ve görünür şekilde** kaydedilmiştir.

---

## 💡 Yeni Strateji Ekleme ve Test Etme

Sistem tam modüler olduğundan, 6 hissenin tamamında aynı anda çalışacak yeni bir algoritma geliştirmek son derece kolaydır:

```python
# 1. strategies/yeni_stratejim.py oluşturun:
from strategy_base import StrategyBase
from indicators import add_ema, add_rsi, add_atr

class SuperTrendStrategy(StrategyBase):
    def __init__(self, ema_fast=9, ema_slow=21, rsi_period=14):
        super().__init__(name="SuperTrend", params={"fast": ema_fast, "slow": ema_slow})
        self.fast = ema_fast
        self.slow = ema_slow
        self.rsi = rsi_period

    def prepare_data(self, df):
        df = add_ema(df, self.fast)
        df = add_ema(df, self.slow)
        df = add_rsi(df, self.rsi)
        df = add_atr(df, 14)
        return df

    def generate_signals(self, df):
        df["Signal"] = 0
        buy_cond = (df[f"EMA_{self.fast}"] > df[f"EMA_{self.slow}"]) & (df[f"RSI_{self.rsi}"] > 50)
        sell_cond = (df[f"EMA_{self.fast}"] < df[f"EMA_{self.slow}"])
        df.loc[buy_cond, "Signal"] = 1
        df.loc[sell_cond, "Signal"] = -1
        return df

# 2. runner.py veya notebook üzerinden 6 hissede test edin:
from runner import run_pipeline
from risk_manager import RiskManager

strategy = SuperTrendStrategy()
rm = RiskManager(stop_loss_pct=0.06, trailing_stop_pct=0.04)
results, eval_res, df_summary = run_pipeline(strategy, rm)
```

---

## 📊 Örnek Strateji Sonuçları (Baseline SMA Crossover)

Tek tip SMA Crossover (10/50) + %5 Stop-Loss + %3 Trailing Stop ile yapılan ilk doğrulama testi sonuçları:

| Hisse | Başlangıç | Final Sermaye | Net Kâr | Benchmark Hedefi | Fark (TL) | Durum | Trades | Win Rate | Max DD |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | 102,389 TL | +2,389 TL | 184,000 TL | -81,611 TL | ❌ **FAIL** | 5 | %40.0 | -%9.4 |
| **ASELS** | 100,000 TL | 101,570 TL | +1,570 TL | 339,000 TL | -237,430 TL | ❌ **FAIL** | 2 | %50.0 | -%2.8 |
| **TUPRS** | 100,000 TL | 106,242 TL | +6,242 TL | 172,000 TL | -65,758 TL | ❌ **FAIL** | 5 | %40.0 | -%9.8 |
| **TCELL** | 100,000 TL | 93,759 TL | -6,241 TL | 82,000 TL | **+11,759 TL** | ✅ **PASS** | 11 | %27.3 | -%9.8 |
| **FROTO** | 100,000 TL | 106,303 TL | +6,303 TL | 103,000 TL | **+3,303 TL** | ✅ **PASS** | 3 | %66.7 | -%5.3 |
| **EREGL** | 100,000 TL | 96,689 TL | -3,311 TL | 139,000 TL | -42,311 TL | ❌ **FAIL** | 4 | %25.0 | -%5.3 |
| **TOPLAM**| **600,000 TL** | **606,952 TL** | **+6,952 TL** | **1,019,000 TL** | **-412,048 TL** | **2/6 PASS** | **30** | **%36.7** | **-%9.8** |

> 🔍 **Neden Bazı Hisseler Geçti, Bazıları Kaldı?**  
> Bu sorunun ampirik piyasa dinamikleri, rejim farkları ve volatilite analizleriyle detaylı yanıtı için [`analysis_report.md`](analysis_report.md) dosyasını inceleyiniz.

---

## 📈 Üretilen Grafikler (`results/charts/`)

| Görsel Dosyası | Açıklama |
|---|---|
| `AKBNK_dashboard.png` | AKBNK 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `ASELS_dashboard.png` | ASELS 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `TUPRS_dashboard.png` | TUPRS 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `TCELL_dashboard.png` | TCELL 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `FROTO_dashboard.png` | FROTO 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `EREGL_dashboard.png` | EREGL 3-in-1 Fiyat, İşlemler, Equity Curve ve PnL Paneli |
| `benchmark_comparison.png` | 6 hisse Benchmark vs Strateji Final Sermaye Karşılaştırma Bar Grafiği |
| `all_equity_curves.png` | Tüm hisselerin portföy sermaye değişim eğrileri |

---

## 🏁 Tamamlanan Fazlar

- [x] **Phase 1:** Config + Data Loader (Cache, yfinance entegrasyonu, doğrulama)
- [x] **Phase 2:** İndikatör Kütüphanesi (15+ teknik indikatör)
- [x] **Phase 3:** Strateji Base + Örnek Strateji (No Look-Ahead standardı)
- [x] **Phase 4:** Risk Manager (Stop-loss, trailing stop, ATR stop, full capital sizing)
- [x] **Phase 5:** Backtest Motoru (Trade nesnesi, mark-to-market equity curve)
- [x] **Phase 6:** Performans Metrikleri & Benchmark Kontrolü (15+ metrik, PASS/FAIL analizi)
- [x] **Phase 7:** Görselleştirme (3-in-1 detaylı paneller ve karşılaştırma çizimleri)
- [x] **Phase 8:** Runner CLI & Teslim Jupyter Notebook'u (`main_notebook.ipynb`)
- [x] **Phase 9:** Final Analiz ve Strateji Raporu (`analysis_report.md`)