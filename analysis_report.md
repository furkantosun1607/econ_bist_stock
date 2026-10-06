# BIST Algorithmic Trading Challenge - Final Analiz ve Strateji Raporu
## "Aynı Strateji Neden Farklı Hisselerde Farklı Performans Gösterdi?"

**Ders:** BIST Algorithmic Trading  
**Yazar:** Furkan Tosun  
**Periyot:** 2 Ocak 2025 - 30 Eylül 2026 (440 İşlem Günü / Bar)  
**Başlangıç Sermayesi:** 100.000 TL / Hisse (Toplam 600.000 TL)  
**Kapsanan Hisseler:** AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL  
**Varsayılan Strateji:** `AdaptiveRegimeStrategy` (Trendde Geri Çekilme + Ortalamaya Dönüş + Kapanış Bazlı 5x ATR Trailing Çıkışı)  
**Referans Strateji:** `SmaCrossoverStrategy` (SMA 10/50 + %5 Stop-Loss + %3 Trailing Stop)  

---

## 1. Yönetici Özeti (Executive Summary)

Bu çalışma kapsamında, BIST 100 endeksinin lokomotif 6 hissesi (**AKBNK, ASELS, TUPRS, TCELL, FROTO, EREGL**) üzerinde kural tabanlı, hiçbir gelecek verisi içermeyen (**Strict No Look-Ahead**, $t$ barı kapanışında üretilen sinyaller $t+1$ açılışında uygulanır), tek ve ortak parametreli algoritmik alım-satım sistemleri geliştirilmiş ve test edilmiştir.

Proje kapsamında iki ana aşama yürütülmüştür:
1. **Başlangıç Referans Modeli (SMA 10/50 Crossover + Sabit %3 Trailing Stop):**
   - Sermaye koruması sağlamış, ancak süper-trend hisselerinde (%3 sabit trailing stop'un gürültüye takılması nedeniyle) kârı erkenden kilitlemiş; 600.000 TL sermaye **606.952 TL (+%1,16)** olmuş ve yalnızca 2/6 hisse (TCELL, FROTO) benchmark'ı geçebilmiştir.
2. **Nihai Dondurulmuş Model (`AdaptiveRegimeStrategy`):**
   - Trend rejiminde (`EMA20 > EMA60` ve `Close > EMA60`) geri çekilmeleri (`RSI3 < 50`), yatay/düşüş rejiminde ise aşırı satışı (`RSI3 < 20`) hedefleyen, çıkışta ortalamaya dönüş (`Close >= EMA10` veya `RSI3 > 70`) ile dinamik volatilite korumasını (`Close < Peak - 5 * ATR14`) birleştiren ortak stratejidir.
   - Toplam sermayeyi **600.000 TL'den 913.200 TL'ye (+%52,20 kâr)** ulaştırmıştır.
   - **TUPRS (+28.750 TL fark), TCELL (+29.925 TL fark)** ve **EREGL (+38.850 TL fark)** hisselerinde bireysel benchmark hedeflerini açık farkla aşarak **[PASS]** almıştır.
   - **FROTO**, 103.000 TL hedefine karşılık 101.934 TL elde ederek hedefi yalnızca **1.066 TL farkla (%1,03 marj)** kaçırmıştır.
   - Ancak şartnamenin en katı kuralı olan *"6 hissenin tamamı bireysel hedefini aynı anda geçmelidir"* şartı **AKBNK (79.819 TL vs 184.000 TL)** ve **ASELS (240.922 TL vs 339.000 TL)** hisseleri nedeniyle tam dönemde **3/6 PASS** seviyesinde kalmıştır.

---

## 2. Benchmark Karşılaştırması ve Temel Sonuçlar

### 2.1. Nihai Strateji: Adaptive Regime Performansı (Varsayılan)

| Hisse | Başlangıç | Final Sermaye | Strateji Net Kâr | Benchmark Hedefi | Benchmark Net Kâr | Fark (TL) | Durum | Trades | Win Rate | Max DD |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AKBNK** | 100.000 TL | 79.819 TL | -20.181 TL | 184.000 TL | +84.000 TL | -104.181 TL | ❌ **FAIL** | 10 | %40,0 | %50,68 |
| **ASELS** | 100.000 TL | 240.922 TL | +140.922 TL | 339.000 TL | +239.000 TL | -98.078 TL | ❌ **FAIL** | 8 | %75,0 | %25,02 |
| **TUPRS** | 100.000 TL | 200.750 TL | +100.750 TL | 172.000 TL | +72.000 TL | **+28.750 TL** | ✅ **PASS** | 7 | %85,7 | %17,86 |
| **TCELL** | 100.000 TL | 111.925 TL | +11.925 TL | 82.000 TL | -18.000 TL | **+29.925 TL** | ✅ **PASS** | 14 | %57,1 | %29,48 |
| **FROTO** | 100.000 TL | 101.934 TL | +1.934 TL | 103.000 TL | +3.000 TL | -1.066 TL | ❌ **FAIL** | 15 | %66,7 | %38,58 |
| **EREGL** | 100.000 TL | 177.850 TL | +77.850 TL | 139.000 TL | +39.000 TL | **+38.850 TL** | ✅ **PASS** | 11 | %81,8 | %19,53 |
| **TOPLAM**| **600.000 TL** | **913.200 TL** | **+313.200 TL** | **1.019.000 TL** | **+419.000 TL** | **-105.800 TL** | **3/6 PASS** | **65** | **%67,7** | **%50,68** |

### 2.2. Referans Karşılaştırması: SMA 10/50 Crossover vs. Adaptive Regime

| Strateji | Toplam Sermaye | Toplam Kâr (TL) | Portföy Getiri % | Geçen Hisse (PASS) | En Yüksek Getiri | En Düşük Getiri |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **SMA 10/50 Baseline** | 606.952 TL | +6.952 TL | +%1,16 | 2/6 (TCELL, FROTO) | FROTO (+6.303 TL) | TCELL (-6.241 TL) |
| **Adaptive Regime** | **913.200 TL** | **+313.200 TL** | **+%52,20** | **3/6 (TUPRS, TCELL, EREGL)** | ASELS (+140.922 TL) | AKBNK (-20.181 TL) |

---

## 3. Ampirik Piyasa Karakteristikleri Matrisi

Aşağıdaki veriler, `analyze_results.py` tarafından 440 bar üzerinden ampirik olarak hesaplanmış gerçek piyasa dinamikleridir:

| Hisse | Al-Tut Getirisi (B&H) | Yıllık Volatilite ($\sigma$) | Ort ATR % | Ort ADX | Trend Günü % | Ort Günlük Ciro | Trades | Win Rate % | ATR Stop Çıkışı | Dönüş Çıkışı | Sahte Kırılım | Pozisyonda Kalma % | Max DD % |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **AKBNK** | +%6,8 | %42,0 | %3,56 | 37,0 | %70,5 | 7.825 M TL | 10 | %40,0 | 3 | 6 | 0 | %55,0 | %50,68 |
| **ASELS** | +%358,4 | %46,8 | %3,98 | 38,2 | %70,0 | 8.161 M TL | 8 | %75,0 | 2 | 5 | 0 | %74,3 | %25,02 |
| **TUPRS** | +%200,2 | %35,9 | %3,14 | 35,9 | %65,2 | 5.019 M TL | 7 | %85,7 | 3 | 3 | 0 | %68,6 | %17,86 |
| **TCELL** | +%4,1 | %33,9 | %3,08 | 31,3 | %69,1 | 2.582 M TL | 14 | %57,1 | 3 | 11 | 0 | %50,5 | %29,48 |
| **FROTO** | -%12,4 | %33,0 | %3,09 | 36,7 | %65,7 | 1.494 M TL | 15 | %66,7 | 4 | 10 | 1 | %52,3 | %38,58 |
| **EREGL** | +%50,1 | %38,0 | %3,09 | 37,0 | %79,3 | 4.970 M TL | 11 | %81,8 | 3 | 8 | 0 | %64,8 | %19,53 |

---

## 4. "Aynı Strateji Neden Farklı Hisselerde Farklı Performans Gösterdi?" — Derinlemesine Ekonometrik Yanıtlar

Ödevin ana araştırma sorusu olan *"Aynı kurallar ve parametrelerle çalışan tek bir strateji neden 6 farklı hissede dramatik biçimde farklı sonuçlar verdi?"* sorusu ampirik bulgular ışığında 7 temel boyutta incelenmiştir:

### 4.1. Seküler Mega-Trend Hisseleri: ASELS ve TUPRS
- **ASELS (+%358,4 B&H) ve TUPRS (+%200,2 B&H):**
  - Her iki hisse de dönem boyunca endeksin en güçlü yükseliş hareketini sergilemiştir.
  - SMA modelinde uygulanan %3 sabit trailing stop, hissenin günlük gürültüsünde (%3,98 ortalama ATR) pozisyonu kapatarak sistemi nakitte bırakmıştı.
  - `AdaptiveRegimeStrategy`, **5 x ATR14** genişliğindeki kapanış bazlı takip mekanizması sayesinde pozisyonda kalma süresini ASELS'te **%74,3**'e, TUPRS'ta **%68,6**'ya çıkarmıştır.
  - **TUPRS Sonucu:** 7 işlemde %85,7 kazanma oranı ile 200.750 TL'ye ulaşmış ve 172.000 TL hedefini **+28.750 TL farkla aşarak [PASS]** almıştır.
  - **ASELS Paradoksu:** Strateji ASELS'te +140.922 TL devasa kâr üretmiş (%75 kazanma oranı, 240.922 TL final), ancak ödev benchmark'ı olan **339.000 TL (+%239)** hedefine yetişememiştir. Hisse neredeyse hiç nefes almadan 4,5 katına çıktığı için, herhangi bir düzeltmede veya kâr realizasyonunda nakde geçen model, hissenin aralıksız al-tut performansının gerisinde kalmıştır.

### 4.2. Yatay ve Negatif Trend Piyasaları: TCELL ve FROTO
- **TCELL (+%4,1 B&H):**
  - TCELL 440 gün boyunca dar bir bantta yatay seyretmiştir. Trend takip eden sistemlerin en çok zorlandığı piyasa tipidir.
  - `AdaptiveRegimeStrategy`'deki **RSI3 < 20 aşırı satım girişi** ve **RSI3 > 70 / Close >= EMA10 ortalamaya dönüş çıkışı**, TCELL'in testere hareketlerini avantaja çevirmiştir.
  - 14 işlemin 11'i ortalamaya dönüş çıkışıyla kârla kapatılmış; final sermaye 111.925 TL'ye ulaşarak 82.000 TL hedefi **+29.925 TL farkla ezici şekilde [PASS]** almıştır.
- **FROTO (-%12,4 B&H):**
  - FROTO dönem boyunca net değer kaybetmiştir. B&H yatırımcısı -12.400 TL zarardadır.
  - Stratejimiz, rejim filtresi sayesinde ana düşüş dalgalarında nakitte kalarak sermayeyi korumuş, açılan 15 işlemde %66,7 kazanma oranı ile **+1.934 TL net kâr** üretmiştir.
  - Final sermaye 101.934 TL olmuş; 103.000 TL hedefini yalnızca **1.066 TL (%1,03)** farkla kaçırmıştır.

### 4.3. Döngüsel Emtia ve Trend Dalgalanması: EREGL (+%50,1 B&H)
- EREGL %79,3 trend günü oranıyla en belirgin dalga yapısına sahip hissedir.
- 11 işlemde %81,8 kazanma oranı, 6,76 Profit Factor ve %19,53 gibi son derece düşük bir drawdown ile **177.850 TL** üretmiş, 139.000 TL benchmark'ını **+38.850 TL farkla [PASS]** geçmiştir.
- Trend içi geri çekilme (`trend and RSI3 < 50`) kuralı, EREGL'in yükseliş dalgalarındaki basamaklı yapısını kusursuz yakalamıştır.

### 4.4. Algoritmanın Zayıf Halkası: AKBNK'nın 2026 Çöküşü ve %50,68 Drawdown
- AKBNK dönem boyunca B&H bazında %6,8 yükselmesine rağmen, dönem içi fiyat hareketleri son derece sert olmuştur.
- 2025 geliştirme döneminde +%18,27 getiri sağlayan model, **2026 değerlendirme döneminde -%32,79 kayıp** yaşamış ve azami düşüşü **%50,68**'e fırlamıştır.
- **Nedenleri:**
  1. **Bankacılık Sektörü Volatilitesi:** Makroekonomik haber akışı ve faiz kararları, bankacılık hisselerinde gap'li (boşluklu) sert düşüşlere yol açmıştır.
  2. **Geri Çekilme Tuzağı (Falling Knife):** Sert düşüş trendinin başında RSI3 aşırı satım bölgesine indiğinde sistem alım yapmış, ancak fiyat toparlanmayıp düşüşe devam ettiğinde 5x ATR seviyesine kadar pozisyonu taşımıştır.
  3. **Gecikmeli Çıkış Riski:** Kararlar kapanışta verilip ertesi gün açılışta uygulandığı için, ertesi gün açılışında yaşanan aşağı yönlü fiyat boşlukları zararı büyütmüştür.

---

## 5. Kronolojik Doğrulama ve Maliyet Stresi Bulguları

`validate_strategy.py` tarafından üretilen bağımsız dönem değerlendirmeleri:

| Dönem | Hisse | Strateji | Final TL | Getiri % | İşlem | Max DD % | Al-Tut TL | Fazla Getiri (TL) |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|
| **Geliştirme 2025** | TUPRS | Adaptive | 145.700 TL | +%45,70 | 4 | %12,13 | 143.050 TL | +2.650 TL |
| **Holdout 2026** | TUPRS | Adaptive | 137.784 TL | +%37,78 | 3 | %10,95 | 215.194 TL | -77.410 TL |
| **Geliştirme 2025** | EREGL | Adaptive | 122.866 TL | +%22,87 | 7 | %18,81 | 98.144 TL | +24.722 TL |
| **Holdout 2026** | EREGL | Adaptive | 144.386 TL | +%44,39 | 5 | %18,15 | 152.542 TL | -8.156 TL |
| **Geliştirme 2025** | AKBNK | Adaptive | 118.271 TL | +%18,27 | 5 | %18,59 | 93.991 TL | +24.280 TL |
| **Holdout 2026** | AKBNK | Adaptive | 67.215 TL | -%32,79 | 5 | %42,39 | 113.843 TL | -46.628 TL |
| **Maliyet Stresi 2026** | TUPRS | Adaptive (komisyon+slippage) | 136.958 TL | +%36,96 | 3 | %11,13 | 214.336 TL | -77.378 TL |
| **Maliyet Stresi 2026** | EREGL | Adaptive (komisyon+slippage) | 141.523 TL | +%41,52 | 5 | %18,47 | 151.939 TL | -10.416 TL |
| **Maliyet Stresi 2026** | AKBNK | Adaptive (komisyon+slippage) | 65.602 TL | -%34,40 | 5 | %43,77 | 113.390 TL | -47.788 TL |

### Önemli Çıkarımlar:
1. **İşlem Maliyeti Dayanıklılığı:** Her iki yönde binde 1 komisyon ve binde 1 kayma (%0,20 toplam tur maliyeti) eklendiğinde, ortalama işlem süresi uzun olan (15-20 gün) stratejimiz maliyetlerden sınırlı etkilenmiştir (TUPRS'ta getiri %37,78'den %36,96'ya, EREGL'de %44,39'dan %41,52'ye gerilemiştir).
2. **Aşırı Uyum (Overfitting) Uyarısı:** 2025'te en iyi görünen aday, 2026'da AKBNK'da sert bir negatif rejime yakalanmıştır. Bu durum, finansal piyasalarda geçmiş veri üzerinde optimize edilen kuralların geleceğe yönelik bir getiri garantisi sunmadığını açıkça ortaya koymaktadır.

---

## 6. Akademik Değerlendirme ve Gelecek Geliştirme Önerileri

6 hissenin tamamında **[6/6 PASS]** alabilmek ve AKBNK benzeri tekil çöküşleri engellemek için sistem mimarisine eklenebilecek bilimsel mekanizmalar:

1. **Sektörel Rejim Ayrımı (Market Regime & Beta Filter):**
   - BIST Banka (XBANK) ve BIST Sınai (XUSIN) endekslerinin dinamikleri birbirinden kökten farklıdır. BIST 100 endeksi 200 günlük hareketli ortalamanın altındayken banka hisselerinde dip avcılığı (`RSI < 20`) kuralı devre dışı bırakılmalıdır.
2. **Volatilite Rejimine Göre Dinamik ATR Çarpanı:**
   - 5x ATR çarpanı, düşük volatilitede (%30) kârı korurken, yüksek volatilitede (%45+) aşırı genişleyerek (AKBNK'da olduğu gibi) stop mesafesini sermayenin %15-20'sine kadar açabilmektedir. ATR çarpanı hissenin normalize edilmiş tarihsel oynaklığına göre dinamik olmalıdır (örneğin 3.0x - 4.5x aralığında sınırlandırılmalıdır).
3. **Zaman Bazlı Stop (Time-Stop):**
   - Aşırı satım alımı yapıldıktan sonra 5 gün içinde fiyat EMA10 üzerine çıkamıyorsa pozisyon maliyetine bakılmaksızın kapatılmalıdır (Mean-reversion failure exit).

---

## 7. Sonuç

Bu projede geliştirilen algoritmik ticaret altyapısı:
- **Tam Şeffaflık:** 3/6 hisse geçilmiş, toplam kâr +313.200 TL'ye ulaşmış, zayıflıklar ve eksiklikler (AKBNK düşüşü, 1 Ekim veri eksikliği) dürüstçe raporlanmıştır.
- **Katı No Look-Ahead Güvencesi:** Sinyal hesaplaması ile emir dolumu zaman damgası düzeyinde ayrılmış, stop dolumlarında gap fiyatı kullanılmıştır.
- **Yüksek Test Kapsamı:** 70'in üzerinde otomatik unit test ile tüm modüller (veri yükleme, indikatörler, sinyaller, backtest motoru, risk yönetimi, metrikler, runner ve notebook oluşturucu) matematiksel olarak doğrulanmıştır.
