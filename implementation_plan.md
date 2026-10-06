# 📋 BIST Algorithmic Trading Challenge - Implementation Plan

## 🎯 Proje Özeti

6 BIST hissesi (AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL) için **tek bir algoritmik trading stratejisi** geliştirme ve backtesting.

| Parametre | Değer |
|-----------|-------|
| Backtest Dönemi | 1 Ocak 2025 - 1 Ekim 2026 |
| Başlangıç Sermayesi | Her hisse için 100,000 TL |
| Başarı Kriteri | Her hisse **bireysel olarak** benchmark'ını geçmeli |
| Min Trade Sayısı | Her hisse için en az 3 tamamlanmış işlem |

### Benchmark Hedefleri

| Hisse | Benchmark Kâr | Geçilmesi Gereken Final Capital |
|-------|---------------|--------------------------------|
| AKBNK | +84,000 TL | > 184,000 TL |
| ASELS | +239,000 TL | > 339,000 TL |
| TUPRS | +72,000 TL | > 172,000 TL |
| TCELL | -18,000 TL | > 82,000 TL |
| FROTO | +3,000 TL | > 103,000 TL |
| EREGL | +39,000 TL | > 139,000 TL |

> [!IMPORTANT]
> TCELL ve FROTO düşük benchmark'lara sahip (kolay hedef), ASELS çok yüksek (zor hedef). Strateji tüm hisselerde aynı olmalı ama her birini geçmeli.

---

## 🏗️ Mimari Tasarım Felsefesi

Proje **algoritma-agnostik** olarak tasarlanacak. Strateji modülü bir **interface/abstract class** üzerinden çalışacak, böylece farklı algoritmaları **plug-and-play** şeklinde deneyebileceksin.

```
quiz/
├── config.py                   # Sabitler, parametreler, hisse listesi
├── data_loader.py              # Veri çekme ve hazırlama
├── indicators.py               # Teknik indikatör hesaplama kütüphanesi
├── strategy_base.py            # Strateji abstract base class (interface)
├── strategies/                 # Deneme stratejileri (plug-and-play)
│   ├── __init__.py
│   ├── sma_crossover.py        # Örnek: SMA Crossover
│   ├── rsi_mean_reversion.py   # Örnek: RSI Mean Reversion
│   ├── volume_bubbles.py       # Derste gösterilen
│   └── custom_strategy.py      # Senin tasarlayacağın
├── risk_manager.py             # Stop-loss, trailing stop, position sizing
├── backtester.py               # Backtest motoru
├── metrics.py                  # Performans metrikleri hesaplama
├── visualizer.py               # Grafik ve chart üretimi
├── runner.py                   # Ana çalıştırıcı (tüm hisseleri döngüyle çalıştırır)
├── main_notebook.ipynb         # Teslim edilecek Jupyter Notebook
└── results/                    # Çıktılar
    ├── trades/                 # Her hisse için trade logları
    └── charts/                 # Her hisse için grafikler
```

> [!TIP]
> Bu yapıda yeni strateji denemek için sadece `strategies/` altına yeni bir dosya eklemen ve `runner.py`'da strateji adını değiştirmen yeterli. Backtest motoru, metrikler ve görselleştirme hiç değişmeden çalışır.

---

## 📦 Phase'ler

### Phase 1: Temel Altyapı (Config + Data)
**Hedef:** Veri pipeline'ını kurup tüm hisseler için temiz OHLCV verisi elde etmek.

**Dosyalar:**
- `config.py` → Sabitler ve parametreler
- `data_loader.py` → `yfinance` ile veri çekme, cache'leme

**Detaylar:**
```python
# config.py içeriği
STOCKS = ["AKBNK.IS", "ASELS.IS", "TUPRS.IS", "TCELL.IS", "FROTO.IS", "EREGL.IS"]
START_DATE = "2025-01-01"
END_DATE = "2026-10-01"
INITIAL_CAPITAL = 100_000
BENCHMARKS = {
    "AKBNK.IS": 184_000,
    "ASELS.IS": 339_000,
    # ...
}
```

**Çıktı:** Her hisse için `pd.DataFrame` (Date, Open, High, Low, Close, Volume)

---

### Phase 2: İndikatör Kütüphanesi
**Hedef:** Stratejilerin kullanabileceği tüm teknik indikatörleri hesaplayan modüler bir kütüphane.

**Dosya:** `indicators.py`

**Hesaplanacak İndikatörler:**
| İndikatör | Açıklama | Kullanım Alanı |
|-----------|----------|----------------|
| SMA(n) | Simple Moving Average | Trend takibi |
| EMA(n) | Exponential Moving Average | Trend takibi |
| RSI(n) | Relative Strength Index | Aşırı alım/satım |
| MACD | Moving Average Convergence Divergence | Momentum |
| Bollinger Bands | Bant genişliği ve pozisyon | Mean reversion |
| ATR(n) | Average True Range | Volatilite / Stop-loss |
| Volume SMA | Hacim ortalaması | Hacim analizi |
| Stochastic | %K ve %D | Momentum |
| Support/Resistance | Destek/Direnç seviyeleri | Breakout |
| ADX | Average Directional Index | Trend gücü |

> [!NOTE]
> Her indikatör bağımsız bir fonksiyon olarak yazılacak. Strateji sadece ihtiyaç duyduklarını çağıracak.

---

### Phase 3: Strateji Altyapısı (Abstract Base + İlk Örnek)
**Hedef:** Tüm stratejilerin uyması gereken interface'i tanımlamak.

**Dosyalar:**
- `strategy_base.py` → Abstract Base Class
- `strategies/sma_crossover.py` → Basit bir test stratejisi

**Strateji Interface'i:**
```python
class StrategyBase(ABC):
    def __init__(self, params: dict):
        """Strateji parametreleri (period, threshold vs.)"""
        
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input: OHLCV + indikatörler içeren DataFrame
        Output: 'signal' kolonu eklenmiş DataFrame
                signal = 1 (BUY), -1 (SELL), 0 (HOLD)
        """
        
    def get_name(self) -> str:
        """Strateji adı (raporlama için)"""
        
    def get_params(self) -> dict:
        """Aktif parametreler (raporlama için)"""
```

> [!IMPORTANT]
> Bu interface sayesinde yeni strateji denemek çok basit:
> 1. `StrategyBase`'den türet
> 2. `generate_signals()` metodunu yaz
> 3. `runner.py`'da stratejini seç → Çalıştır

---

### Phase 4: Risk Yönetimi Modülü
**Hedef:** Stratejiden bağımsız risk yönetimi mekanizmaları.

**Dosya:** `risk_manager.py`

**Mekanizmalar:**
- **Stop-Loss:** Sabit yüzde bazlı (ör. -%5)
- **Trailing Stop:** ATR bazlı veya yüzde bazlı
- **Maximum Holding Period:** Belirli gün sonra zorla çıkış
- **Position Sizing:** Sermayenin ne kadarıyla giriş yapılacak
- **Chandelier Exit:** ATR bazlı trailing stop varyantı

```python
class RiskManager:
    def __init__(self, stop_loss_pct=None, trailing_stop_pct=None, 
                 atr_multiplier=None, max_holding_days=None):
        ...
    
    def check_exit(self, entry_price, current_price, high_since_entry, 
                   current_atr, days_held) -> bool:
        """Pozisyondan çıkış gerekiyor mu?"""
    
    def calculate_position_size(self, capital, price, atr) -> int:
        """Kaç lot alınmalı?"""
```

> [!NOTE]
> Risk manager stratejiden **tamamen bağımsız**. İstediğin stratejiyle istediğin risk yönetimi kombinasyonunu kullanabilirsin.

---

### Phase 5: Backtest Motoru
**Hedef:** Sinyalleri alıp gerçekçi bir simülasyonla trade'leri yürütmek.

**Dosya:** `backtester.py`

**Özellikler:**
- Signal bazlı trade execution
- Commission/slippage desteği (opsiyonel)
- Trade log tutma (her trade için: entry_date, entry_price, exit_date, exit_price, pnl)
- Equity curve hesaplama
- No look-ahead garantisi (sadece o ana kadar olan veri kullanılır)

```python
class Backtester:
    def __init__(self, initial_capital, risk_manager):
        ...
    
    def run(self, df_with_signals: pd.DataFrame) -> BacktestResult:
        """
        Returns:
            BacktestResult with:
                - trades: List[Trade]  (her trade'in detayı)
                - equity_curve: pd.Series
                - final_capital: float
        """
```

**Trade Veri Yapısı:**
```python
@dataclass
class Trade:
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str  # "signal", "stop_loss", "trailing_stop", "max_hold"
```

---

### Phase 6: Performans Metrikleri
**Hedef:** Gerekli tüm metrikleri hesaplamak ve benchmark ile karşılaştırmak.

**Dosya:** `metrics.py`

**Zorunlu Metrikler:**
| Metrik | Formül/Açıklama |
|--------|----------------|
| Net Profit | Final Capital - Initial Capital |
| Final Capital | Son sermaye |
| Total Trades | Toplam tamamlanmış işlem sayısı |
| Winning Trades | Kârlı işlem sayısı |
| Losing Trades | Zararlı işlem sayısı |
| Win Rate | Winning / Total × 100 |
| Maximum Drawdown | Equity curve üzerinden max düşüş |
| Profit Factor | Gross Profit / Gross Loss |
| Average Trade | Ortalama trade P&L |

**Benchmark Karşılaştırma:**
```python
def compare_with_benchmark(final_capital: float, stock: str) -> dict:
    """PASS/FAIL ve fark bilgisi döner"""
```

---

### Phase 7: Görselleştirme
**Hedef:** Her hisse için trade'leri ve performansı gösteren grafikler.

**Dosya:** `visualizer.py`

**Üretilecek Grafikler (Her hisse için):**
1. **Fiyat + Trade Grafiği:** Fiyat çizgisi üzerinde BUY (▲ yeşil) ve SELL (▼ kırmızı) işaretleri
2. **Equity Curve:** Sermaye değişim grafiği
3. **Trade P&L Bar Chart:** Her trade'in kâr/zarar barı
4. **Benchmark Karşılaştırma:** Final capital vs benchmark tablosu/grafiği

---

### Phase 8: Runner & Jupyter Notebook
**Hedef:** Tüm parçaları birleştirip 6 hisseyi çalıştırmak.

**Dosyalar:**
- `runner.py` → Komut satırından çalıştırma
- `main_notebook.ipynb` → Teslim notebook'u

**Runner Akışı:**
```
1. Config'den hisse listesini al
2. Her hisse için:
   a. Veriyi yükle (data_loader)
   b. İndikatörleri hesapla (indicators)
   c. Strateji sinyallerini üret (strategy.generate_signals)
   d. Backtest'i çalıştır (backtester.run)
   e. Metrikleri hesapla (metrics)
   f. Grafikleri üret (visualizer)
   g. Benchmark ile karşılaştır
3. Özet tablo yazdır (6 hisse × tüm metrikler)
4. PASS/FAIL sonuçlarını göster
```

---

### Phase 9: Analiz ve Final Rapor
**Hedef:** "Aynı strateji neden farklı hisselerde farklı performans gösterdi?" sorusunu yanıtlamak.

**Tartışılacak Faktörler:**
- Trending vs Sideways piyasa yapısı
- Volatilite farkları
- False breakout sıklığı
- Momentum gücü
- Hacim karakteristikleri
- Stop-loss tetiklenme sıklığı

---

## 🔄 Strateji Değiştirme Akışı

Yeni bir strateji denemek istediğinde:

```
1. strategies/ altına yeni_strateji.py oluştur
2. StrategyBase'den türet
3. generate_signals() metodunu yaz
4. runner.py'da:
   strategy = YeniStrateji(params={...})
5. Çalıştır → Sonuçları gör
```

Hiçbir zaman backtester, metrics, visualizer, data_loader değişmez. **Sadece strateji modülü değişir.**

---

## ⚡ İlerleme Sırası

| Phase | İçerik | Bağımlılık | Durum |
|-------|--------|------------|-------|
| **Phase 1** | Config + Data Loader | - | ✅ Tamamlandı |
| **Phase 2** | İndikatör Kütüphanesi | Phase 1 | ⬜ Bekliyor |
| **Phase 3** | Strateji Base + Örnek | Phase 2 | ⬜ Bekliyor |
| **Phase 4** | Risk Manager | - | ⬜ Bekliyor |
| **Phase 5** | Backtest Motoru | Phase 3, 4 | ⬜ Bekliyor |
| **Phase 6** | Metrikler | Phase 5 | ⬜ Bekliyor |
| **Phase 7** | Görselleştirme | Phase 5, 6 | ⬜ Bekliyor |
| **Phase 8** | Runner + Notebook | Tümü | ⬜ Bekliyor |
| **Phase 9** | Analiz Raporu | Phase 8 | ⬜ Bekliyor |

> [!TIP]
> Phase 1-2 ve Phase 4 paralel ilerleyebilir çünkü birbirinden bağımsız.

---

## 📦 Gerekli Kütüphaneler

```
yfinance          # BIST veri çekme
pandas            # Veri işleme
numpy             # Hesaplamalar
matplotlib        # Grafik
ta                # Teknik analiz indikatörleri (opsiyonel, elle de yazabiliriz)
```

---

## ❓ Karar Noktaları (Sana Bırakılan)

1. **Strateji Seçimi:** Dersten biri mi, kendi tasarımın mı, yoksa hybrid mi?
2. **Risk Parametreleri:** Stop-loss %, trailing stop multiplier vs.
3. **İndikatör Parametreleri:** SMA period, RSI period vs.
4. **Position Sizing:** Full capital mi, kısmi mi?
5. **Commission:** Hesaba katılacak mı?

---

> [!CAUTION]
> **No Look-Ahead Kuralı:** Strateji yazarken gelecek fiyatları kullanmak yasak. `generate_signals()` sadece o ana kadar olan veriyle çalışmalı. Backtest motoru bunu garanti edecek şekilde tasarlanacak.
