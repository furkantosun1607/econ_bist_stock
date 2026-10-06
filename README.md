# BIST Algorithmic Trading Challenge

Altı BIST hissesi için tek, ortak ve gelecek veri kullanmayan strateji geliştirme projesi. Varsayılan strateji `AdaptiveRegimeStrategy`: trendde geri çekilmeden alım (`pullback=53.0`) + aşırı satımda ortalamaya dönüş (`RSI(3) < 20`) + 3.5x'ten 2.3x ATR'ye daralan dinamik kâr kilitleme + %7 kapanış koruma stopu.

**Sonuç: mevcut veri üzerinde 5/6 benchmark hedefini başarıyla geçmektedir (PASS).** Toplam portföy sermayesi 600.000 TL'den 1.030.925 TL'ye (+%71,82 net kâr) yükselmiştir. Bireysel hisse bazında ASELS (+10.082 TL), TUPRS (+33.828 TL), EREGL (+4.049 TL), FROTO (+18.057 TL) ve TCELL (+618 TL) hedeflerini aşmıştır.

## Çalıştırma

```bash
pip install -r requirements.txt
python runner.py                         # Adaptive_Regime, next_open, grafikler ve trade logları
python runner.py --no-charts             # Hızlı çalışma
python validate_strategy.py              # 2025 / 2026 / alt dönemler / maliyet stresi
python select_strategy.py                # Yalnızca 2025'teki aday karşılaştırmasını yeniden üret
python build_notebook.py                 # Çalıştırılmış, grafikleri gömülü teslim notebook'u
python -m unittest discover -s . -p "test_*.py"
```

SMA referansını çalıştırmak için:

```bash
python runner.py --strategy sma_crossover --fast 10 --slow 50 --stop-loss 0.05 --trailing-stop 0.03
```

Runner sonuçları `results/` içine yazar. SMA komutu da aynı çıktı dosyalarını yeniler; teslim öncesi varsayılan stratejiyi tekrar çalıştırın. `--force-download` önbellek yerine sağlayıcıdan veri okur; mevcut CSV'leri değiştirmez. Varsayılan çalışma çevrimdışı önbelleği kullanır.

## Ortak strateji kuralları

Tüm hisseler aynı parametrelerle, bağımsız 100.000 TL hesaplarda çalışır. Hisse adına, benchmark'a veya elle seçilmiş işlem tarihlerine göre sinyal üretilmez.

1. İlk 50 gözlem göstergeler için hazırlık dönemidir; ilk karar 50. kapanışta alınabilir.
2. Yükseliş rejimi: `EMA15 > EMA50` ve `Close > EMA50`.
3. Alım: yükseliş rejiminde `RSI3 < 53` veya herhangi bir rejimde `RSI3 < 20`.
4. Normal çıkış: yükseliş rejimi dışındayken `RSI3 > 70` veya `Close >= EMA10`.
5. Trend çıkışı: `Close < EMA50`.
6. Dinamik ATR Takip Eden Stop: `3.5 * ATR14`, tepe kazancı >= %20 olunca `2.3 * ATR14` seviyesine daraltılarak kâr kilitlenir.
7. Kapanış koruma stopu: Pozisyon kapanışta giriş fiyatının %7 altına düşerse ertesi açılışta çıkış yapılır.
8. Kararlar kapanışta verilir, **bir sonraki açılışta** (`next_open`) uygulanır; geleceğe bakma hatası (look-ahead) yoktur.
9. Mevcut nakdin tamamıyla tam lot alınır; kaldıraç ve açığa satış yoktur. Yuvarlama sonrası nakit hesapta kalır.

`Signal=1` istenen uzun pozisyonu, `Signal=-1` nakdi ifade eder; hazırlıkta `0` üretilir. Tekrarlanan alım sinyalleri yeni lot eklemez. Aynı strateji nesnesi hisseler arasında durum taşımaz. En az üç işlem şartını sağlamak için yapay al-sat yapılmaz.

## Strateji seçimi ve doğrulama

- [Seçim kayıtları](results/validation/development_candidates.csv)
- [Ayrı dönem ve maliyet testi](results/validation/report.md)
- [Veri özeti, parametreler ve SHA-256 kayıtları](results/validation/manifest.json)
- [Sonuçların nedenleri ve sınırlamaları](analysis_report.md)

## Mevcut sonuçlar

Yerel örneklem: **2 Ocak 2025 – 30 Eylül 2026, 440 bar**. İstenen 1 Ekim 2026 verisi önbellekte bulunmuyor; aşağıdaki sonuçlar bu nedenle geçicidir. Veri yapısal kontrollerden geçti; kaynağı bağımsız olarak doğrulanmadı.

| Hisse | Final TL | Hedef TL | Fark TL | İşlem | Win % | Profit Factor | Max DD % | Örneklem sonucu |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **ASELS** | 349.082 TL | 339.000 TL | **+10.082 TL** | 23 | %65.2 | 6.03 | -%19.0 | **PASS** |
| **TUPRS** | 205.828 TL | 172.000 TL | **+33.828 TL** | 24 | %50.0 | 6.20 | -%14.6 | **PASS** |
| **EREGL** | 143.049 TL | 139.000 TL | **+4.049 TL** | 29 | %34.5 | 2.08 | -%23.9 | **PASS** |
| **FROTO** | 121.057 TL | 103.000 TL | **+18.057 TL** | 46 | %47.8 | 1.39 | -%18.8 | **PASS** |
| **TCELL** | 82.618 TL | 82.000 TL | **+618 TL** | 42 | %40.5 | 0.65 | -%29.6 | **PASS** |
| **AKBNK** | 129.290 TL | 184.000 TL | -54.710 TL | 38 | %44.7 | 1.46 | -%16.9 | FAIL |
| **TOPLAM** | **1.030.925 TL** | — | — | **202** | — | — | — | **5 / 6 PASS** |

2026 ayrı değerlendirmesinde AKBNK **-%32,79**, FROTO **+%1,30** getirdi. Her yönde %0,10 komisyon + %0,10 kayma eklendiğinde bunlar **-%34,40** ve **-%1,88** oluyor. Pozitif toplam sonuç bu zayıflıkları gizlememelidir.

## Dosyalar ve teslim

| Dosya | Görevi |
|---|---|
| `strategies/adaptive_regime.py` | Varsayılan ortak strateji ve açıklanabilir sinyal kolonları |
| `select_strategy.py` | 2025 aday karşılaştırmasının yeniden üretimi |
| `validate_strategy.py` | Tarih sıralı değerlendirme, al-tut referansı, maliyet stresi |
| `runner.py` | CLI, trade CSV'leri, grafikler, metrikler, çalışma ayarları |
| `backtester.py`, `risk_manager.py` | Sonraki açılış emirleri, geçmiş ATR ile gün içi risk kontrolleri |
| `data_loader.py` | OHLCV doğrulama, kapsama ve veri kaynağı bilgileri |
| `metrics.py` | Bireysel hedef, minimum işlem ve eksik kapsam kontrolleri |
| `analyze_results.py` | Rejim, oynaklık, çıkış nedenleri ve pozisyonda kalma analizi |
| `build_notebook.py` | Kodları gerçekten çalıştırır; hatada durur; PNG'leri notebook'a gömer |
| `main_notebook.ipynb` | Kod, görünür sonuçlar, tüm işlemler ve sekiz grafik |
| `results/trades/` | Her işlem için tarih, tam hesaplanan fiyat, adet ve P&L (CSV fiyat sunumu 4 ondalık) |
| `results/metrics_report.md` | Son çalışma performansı ve gerçek veri kapsamı |
| `results/run_metadata.json` | Kullanılan parametreler, maliyetler, veri dosyası özetleri |

Testler; gelecekteki veriyi değiştirince geçmiş sinyallerin değişmemesini, veri kesitleriyle aynı sinyallerin üretilmesini, ATR zamanlamasını, fiyat boşluğu sırasında stop dolumunu, minimum işlem şartını ve değerlendirme sınırındaki emirleri kontrol eder.

## Araştırma dayanağı

Trend bileşeni için [Moskowitz, Ooi ve Pedersen'in zaman serisi momentum araştırması](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum) genel bir motivasyondur; çalışmanın piyasaları ve ufku bu kısa vadeli BIST modelini doğrulamaz. Sınırlı arama ve ayrı değerlendirme yaklaşımı, [Bailey ve arkadaşlarının backtest aşırı uyum çalışmasında](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) ele alınan seçim riskini görünür kılmak içindir; bu projede PBO tahmini yapılmaz.
