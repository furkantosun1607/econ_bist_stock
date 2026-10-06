# BIST Algorithmic Trading Challenge

Altı BIST hissesi için tek, ortak ve gelecek veri kullanmayan strateji geliştirme projesi. Varsayılan strateji `AdaptiveRegimeStrategy`: trendde geri çekilmeden alım + trend dışında ortalamaya dönüş + kapanış bazlı ATR çıkışı.

**Sonuç: mevcut veri üzerinde 3/6 benchmark geçiliyor. Challenge henüz başarılı değil.** Toplam 600.000 TL, 913.200 TL'ye çıktı; önceki SMA örneğinde 606.952 TL idi. Bu artış her hisseyi geçme şartının yerine geçmez. AKBNK'nın %50,68 maksimum düşüşü, algoritmanın önemli bir zayıflığıdır; canlı kullanıma hazır veya küresel olarak en iyi algoritma olduğu iddia edilmez.

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

1. İlk 60 gözlem göstergeler için hazırlık dönemidir; ilk karar 60. kapanışta alınabilir.
2. Yükseliş rejimi: `EMA20 > EMA60` ve `Close > EMA60`.
3. Alım: yükseliş rejiminde `RSI3 < 50` veya herhangi bir rejimde `RSI3 < 20`.
4. Normal çıkış: yükseliş rejimi dışındayken `RSI3 > 70` veya `Close >= EMA10`.
5. Risk çıkışı: `Close < peak - 5 * ATR14`. ATR, Wilder üstel yumuşatmasıyla hesaplanır. Tepe giriş açılışından başlar, sonraki kapanışlarla güncellenir. ATR artınca eşik gevşeyebilir; bu bir sabit zarar limiti değildir.
6. Kararlar kapanışta verilir, **bir sonraki açılışta** uygulanır. ATR çıkışı gün içi stop emri değildir; sonraki açılışta fiyat boşluğu oluşabilir.
7. Mevcut nakdin tamamıyla tam lot alınır; kaldıraç ve açığa satış yoktur. Yuvarlama sonrası nakit hesapta kalır. Ana değerlendirmede komisyon ve kayma sıfırdır.

`Signal=1` istenen uzun pozisyonu, `Signal=-1` nakdi ifade eder; hazırlıkta `0` üretilir. Tekrarlanan alım sinyalleri yeni lot eklemez. Aynı strateji nesnesi hisseler arasında durum taşımaz. En az üç işlem şartını sağlamak için yapay al-sat yapılmaz.

Ek `--stop-loss` / `--trailing-stop` verilirse motor bunları ayrıca uygular. Bunlar varsayılan modelin dışındadır; stratejinin içindeki sanal pozisyon durumunu sıfırlamaz ve model uzun kalmak istiyorsa yeniden giriş olabilir. Adaptive stratejisi `same_close` modunu reddeder.

## Strateji seçimi ve doğrulama

Sınırlı 24 aday yalnızca **2025 verisinde** karşılaştırıldı. İşlem yeterliliği, en zayıf hissenin getirisi, medyan getiri ve düşüş sırası kullanıldı. Bu, tek hissede büyük kâr uğruna diğerlerini ihmal etmemek için kullanılan bir seçim ölçütüdür; altı farklı tam dönem benchmark'ını doğrudan eniyilemez.

Seçilen parametreler sabitlendikten sonra 2026 değerlendirmesi yapıldı. Bu değerlendirmenin ardından parametreler değiştirilmedi. Tam dönem sonucu geliştirme verisi içerir; bağımsız ileri test değildir. Tarihsel ayırma da tek başına gelecekteki başarıyı kanıtlamaz.

- [Seçim kayıtları](results/validation/development_candidates.csv)
- [Ayrı dönem ve maliyet testi](results/validation/report.md)
- [Veri özeti, parametreler ve SHA-256 kayıtları](results/validation/manifest.json)
- [Sonuçların nedenleri ve sınırlamaları](analysis_report.md)

## Mevcut sonuçlar

Yerel örneklem: **2 Ocak 2025 – 30 Eylül 2026, 440 bar**. İstenen 1 Ekim 2026 verisi önbellekte bulunmuyor; aşağıdaki sonuçlar bu nedenle geçicidir. Veri yapısal kontrollerden geçti; kaynağı bağımsız olarak doğrulanmadı. Yeni indirmelerde son tarihin dahil edilmesi düzeltildi; mevcut veriler değiştirilmedi.

| Hisse | Final TL | Hedef TL | İşlem | Max DD % | Örneklem sonucu |
|---|---:|---:|---:|---:|---|
| AKBNK | 79.818,61 | 184.000 | 10 | 50,68 | FAIL |
| ASELS | 240.922,33 | 339.000 | 8 | 25,02 | FAIL |
| TUPRS | 200.750,16 | 172.000 | 7 | 17,86 | PASS |
| TCELL | 111.925,09 | 82.000 | 14 | 29,48 | PASS |
| FROTO | 101.934,34 | 103.000 | 15 | 38,58 | FAIL |
| EREGL | 177.849,68 | 139.000 | 11 | 19,53 | PASS |

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
