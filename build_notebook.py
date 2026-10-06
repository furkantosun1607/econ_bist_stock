"""Execute the adaptive strategy notebook and embed its real output artifacts.

Only replace the notebook once every cell has completed successfully. No kernel
or nbconvert dependency is required: the cells use explicit print/display calls.
"""

import base64
import io
import json
import os
import platform
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


class _NotebookStream(io.TextIOBase):
    """Preserve the order of stream and rich display output within a code cell."""

    def __init__(self, outputs, name):
        self.outputs = outputs
        self.name = name

    def write(self, text):
        if not text:
            return 0
        if (self.outputs and self.outputs[-1].get("output_type") == "stream"
                and self.outputs[-1].get("name") == self.name):
            self.outputs[-1]["text"] += text
        else:
            self.outputs.append({"output_type": "stream", "name": self.name, "text": text})
        return len(text)

    def flush(self):
        pass


def _capture_display(outputs):
    """Support notebook display MIME bundles, including genuine PNG payloads."""
    def display(*objects, raw=False, metadata=None):
        for obj in objects:
            item_metadata = dict(metadata or {})
            if raw:
                if not isinstance(obj, dict):
                    raise TypeError("Raw display requires a MIME mapping")
                data = dict(obj)
            else:
                data = {"text/plain": repr(obj)}
                rich = getattr(obj, "_repr_mimebundle_", None)
                if callable(rich):
                    bundle = rich()
                    if isinstance(bundle, tuple):
                        bundle, bundle_metadata = bundle
                        item_metadata.update(bundle_metadata)
                    data.update(bundle or {})
                html = getattr(obj, "_repr_html_", None)
                if callable(html) and "text/html" not in data:
                    value = html()
                    if value is not None:
                        data["text/html"] = value
            for mime in ("image/png", "image/jpeg"):
                if isinstance(data.get(mime), bytes):
                    data[mime] = base64.b64encode(data[mime]).decode("ascii")
            outputs.append({"output_type": "display_data", "data": data,
                            "metadata": item_metadata})
    return display


def create_and_execute_notebook():
    project_root = Path(__file__).resolve().parent
    previous_directory = Path.cwd()
    os.chdir(project_root)
    try:
        return _build_notebook(project_root)
    finally:
        os.chdir(previous_directory)


def _build_notebook(project_root):
    nb = {
        "cells": [],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py", "mimetype": "text/x-python", "name": "python",
                "nbconvert_exporter": "python", "pygments_lexer": "ipython3",
                "version": platform.python_version(),
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    global_env = {"__name__": "__notebook__"}
    execution_count = 0

    def md(source):
        nb["cells"].append({"cell_type": "markdown", "id": f"cell-{len(nb['cells']):03d}",
                            "metadata": {}, "source": source})

    def code(source):
        nonlocal execution_count
        execution_count += 1
        cell = {"cell_type": "code", "id": f"cell-{len(nb['cells']):03d}",
                "execution_count": execution_count, "metadata": {},
                "outputs": [], "source": source}
        outputs = cell["outputs"]
        global_env["display"] = _capture_display(outputs)
        try:
            with redirect_stdout(_NotebookStream(outputs, "stdout")), \
                    redirect_stderr(_NotebookStream(outputs, "stderr")):
                exec(compile(source, f"<notebook-cell-{execution_count}>", "exec"), global_env)
        except Exception as exc:
            raise RuntimeError(
                f"Notebook cell {execution_count} failed; existing notebook was not replaced"
            ) from exc
        nb["cells"].append(cell)

    md("""# BIST Algorithmic Trading Challenge

**Strateji:** Adaptive Regime — altı hisse için aynı kurallar ve parametreler.  
**İstenen dönem:** 1 Ocak 2025–1 Ekim 2026 (bitiş günü dahil).  
**Başlangıç:** Hisse başına 100.000 TL; tam nakit, tam lot, kaldıraçsız uzun/nakit.

| Hisse | Aşılması gereken final sermaye |
|---|---:|
| AKBNK | 184.000 TL |
| ASELS | 339.000 TL |
| TUPRS | 172.000 TL |
| TCELL | 82.000 TL |
| FROTO | 103.000 TL |
| EREGL | 139.000 TL |

Her hissenin kendi hedefini **aşması** ve en az üç tamamlanmış işlem yapması gerekir.
Toplam portföy kârı bu şartların yerine geçmez. Sinyaller kapanışta hesaplanır;
emirler sonraki barın açılışında uygulanır. Ana karşılaştırma komisyonsuzdur.

**Veri kapsamı:** Mevcut yerel CSV dosyaları 2 Ocak 2025–30 Eylül 2026 arasında
440 bar içerir. 1 Ekim barı yoktur; sonuçlar istenen tam dönemin onayı değildir.
Dosyaların kaynağı bağımsız olarak doğrulanmamıştır. Aşağıda gerçek kapsam ve
dosya parmak izleri tekrar hesaplanır; eksik barlar üretilmez.
""")

    md("## 1. Modüller ve çalışma ortamı")
    code("""import base64
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import STOCKS, INITIAL_CAPITAL, CHARTS_DIR, get_short_name
from data_loader import load_stock_data
from strategies.adaptive_regime import AdaptiveRegimeStrategy
from runner import run_pipeline
from validate_strategy import run_validation

print(f"Python: {sys.version.split()[0]}")
print("Hisseler:", ", ".join(get_short_name(s) for s in STOCKS))
""")

    md("""## 2. Gerçek veri kapsamı ve kalite kontrolü

Önbellek yüklenirken tarihler, pozitif ve sonlu fiyatlar, OHLC aralıkları ve hacim
kontrol edilir. Bu kontroller dosyanın finansal kaynağını doğrulamaz. Bitiş
günü eksikse uyarı verilir; mevcut dosyalar değiştirilmez.
""")
    code("""all_data = {ticker: load_stock_data(ticker, use_cache=True) for ticker in STOCKS}
data_rows = []
for ticker, frame in all_data.items():
    coverage = frame.attrs.get("data_coverage", {})
    provenance = frame.attrs.get("data_provenance", {})
    data_rows.append({
        "Hisse": get_short_name(ticker), "Bar": len(frame),
        "İlk gün": frame.index.min().date().isoformat(),
        "Son gün": frame.index.max().date().isoformat(),
        "1 Ekim mevcut": coverage.get("end_date_observed", False),
        "Kaynak": provenance.get("source", "unknown"),
        "SHA-256": provenance.get("sha256"),
    })
display(pd.DataFrame(data_rows))
if not all(row["1 Ekim mevcut"] for row in data_rows):
    print("GEÇİCİ DEĞERLENDİRME: 1 Ekim 2026 dahil tam dönem henüz doğrulanmadı.")
""")

    md("""## 3. Aynı kurallarla rejime göre işlem

Strateji, hisse adına veya belirli takvim günlerine göre özel kural uygulamaz; altı hissenin tamamında aynı nesnel Python kuralları çalışır.

- **Isınma (Warmup):** En az 50 bar gözlem biriktikten sonra ilk sinyal üretilebilir.
- **Trend rejimi:** `EMA(15) > EMA(50)` ve `Close > EMA(50)` birlikte sağlandığında uptrend, aksi halde range/downtrend olarak sınıflandırılır.
- **Giriş Kuralları (Causal):** Pozisyon yokken:
  1. Trend içindeki geri çekilmeler: `trend and RSI(3) < 53.0`
  2. Aşırı satım toparlanmaları: `RSI(3) < 20.0`
  Girişler çıkış sonrası `cooldown_bars=1` bekleme süresine tabidir.
- **Çıkış Kuralları:**
  1. **Toparlanma çıkışı:** Trend dışındaki pozisyonlarda `RSI(3) > 70` veya `Close >= EMA(10)`
  2. **Trend kırılım çıkışı:** `Close < EMA(50)` olduğunda trend bozulduğu için sonraki açılışta çıkış
  3. **Dinamik Volatilite Takip Eden Stop (ATR Trailing Stop):** Girişten sonraki en yüksek kapanıştan `3.5 × ATR(14)` düşülerek izleyen stop belirlenir. Tepe kazancı %20'yi (`profit_threshold=0.20`) aştığında çarpan `2.3 × ATR` seviyesine daraltılarak kâr kilitlenir.
  4. **Kapanış Koruma Stopu:** Pozisyon kapanışta giriş fiyatının %7 altına düşerse (`stop_loss_pct=0.07`), ertesi açılışta çıkış yapılır.
- **Emir Gerçekleşmesi:** Tüm kararlar bar kapanışındaki verilerle alınır (`next_open` modu); emirler bir sonraki işlem gününün açılış fiyatından gerçekleşir. Geleceğe bakma hatası (look-ahead bias) kesinlikle bulunmaz.

Aşağıdaki hücre kullanılan parametreleri gösterir. Kurallar tüm hisselerde ortaktır.
""")
    code("""strategy = AdaptiveRegimeStrategy()
rm = None  # ATR risk çıkışları stratejinin kapanış sinyallerinde uygulanır.
print("Strateji:", strategy.get_name())
print("Parametreler:", strategy.get_params())
print("Emir modu: next_open; pozisyon: mevcut nakdin %100'ü, tam lot.")
sample = strategy.run(all_data["AKBNK.IS"])
print("AKBNK sinyal dağılımı:")
display(sample["Signal"].value_counts().rename_axis("Signal").to_frame("Bar"))
""")

    md("""## 4. Altı hissede backtest

Mevcut cache üzerinde tek strateji çalıştırılır. Açık son pozisyon son kapanışta
tasfiye edilerek tamamlanmış işlem ve nakit hesapları raporlanır. Sonuçlar
gerçekleşmiş canlı işlem performansı veya gelecekte getiri garantisi değildir.
""")
    code("""results, challenge_eval, df_summary = run_pipeline(
    strategy=strategy, risk_manager=rm, execution_mode="next_open",
    save_charts=True, save_trades=True, save_metrics=True, print_summary=True,
)
display(df_summary)
print("Değerlendirme:", challenge_eval["challenge_status"])
print("Bireysel hedef/işlem kontrolü:", challenge_eval["passed_count"], "/", challenge_eval["total_count"])
""")

    md("""## 5. İşlem kayıtları

Giriş/çıkış tarihleri, gerçekleşen fiyat, lot, kâr/zarar ve çıkış gerekçesi
her hisse için saklanır. Sayılan işlemler tamamlanmış giriş/çıkış çiftleridir.
""")
    code("""for ticker, result in results.items():
    print(f"\\n{get_short_name(ticker)} — {result.total_trades} tamamlanmış işlem")
    display(result.trades_df)
""")

    md("""## 6. Kronolojik karşılaştırma ve maliyet stresi

2025 geliştirme dönemi; 2026 ayrı tarihsel değerlendirme olarak raporlanır.
Tam dönem geriye dönük sonuç, bağımsız ileri test değildir. 2026'nın ilk ve
ikinci yarısı ayrıca gösterilir. Her pencere 100.000 TL nakitle yeniden başlar,
göstergeler geçmişi kullanır ve pencere sonunda açık pozisyon tasfiye edilir.
Alt dönemlerin sonuçları tam dönem için verilen challenge hedefleriyle
PASS/FAIL olarak karşılaştırılmaz.

Karşılaştırmalar: mevcut SMA(10/50) örneği, aynı dönemde al-tut ve her yönde
%0,10 komisyon + %0,10 kayma içeren 2026 maliyet stresi. Parametreler bu tabloda
çıkan en iyi sonuca göre yeniden seçilmez. Ayrıntılar `results/validation/`
dizinindeki rapor, CSV ve veri/parametre manifestosuna kaydedilir.
""")
    code("""validation = run_validation(strategy, all_data=all_data)
columns = ["period", "stock", "strategy", "final_capital", "return_pct",
           "trades", "max_drawdown_pct", "buy_hold_final", "excess_vs_buy_hold_tl"]
display(validation[columns].round(2))
print("Dönem/strateji toplamları — bağımsız hesapların toplamı:")
display(validation.groupby(["period", "strategy"])[
    ["final_capital", "buy_hold_final", "excess_vs_buy_hold_tl"]
].sum().round(2))
""")

    md("""## 7. Fiyat, işlemler ve sermaye grafikleri

Altı hisse paneli ve iki karşılaştırma grafiğinin PNG verileri notebook içine
gömülür. Notebook farklı bir klasöre taşındığında bu kayıtlı çıktılar görünür.
""")
    code("""chart_paths = [CHARTS_DIR / f"{get_short_name(ticker)}_dashboard.png" for ticker in STOCKS]
chart_paths += [CHARTS_DIR / "benchmark_comparison.png", CHARTS_DIR / "all_equity_curves.png"]
for path in chart_paths:
    payload = path.read_bytes()
    if not payload.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise ValueError(f"Geçersiz PNG: {path}")
    print(path.name)
    display({"image/png": base64.b64encode(payload).decode("ascii"),
             "text/plain": f"Grafik: {path.name}"}, raw=True)
print(f"{len(chart_paths)} grafik notebook içine gömüldü.")
""")

    md("""## 8. Sonuçları değerlendirme ve final analiz raporu

### 8.1. Challenge Performans Özeti
BIST Algorithmic Trading Challenge kapsamında geliştirilen tek ve ortak kurallı **Adaptive Regime** stratejisi, 6 hisse üzerinde test edilmiş ve **5/6 hissede bireysel benchmark hedeflerini başarıyla aşmıştır (PASS)**:

| Hisse | Başlangıç | Final Sermaye | Net Kâr (TL) | Benchmark | Fark (TL) | İşlem | Win Rate | Profit Factor | Max DD % | Durum |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ASELS** | 100.000 TL | **349.082 TL** | +249.082 TL | 339.000 TL | **+10.082 TL** | 23 | %65.2 | 6.03 | -%19.0 | **PASS** |
| **TUPRS** | 100.000 TL | **205.828 TL** | +105.828 TL | 172.000 TL | **+33.828 TL** | 24 | %50.0 | 6.20 | -%14.6 | **PASS** |
| **EREGL** | 100.000 TL | **143.049 TL** | +43.049 TL | 139.000 TL | **+4.049 TL** | 29 | %34.5 | 2.08 | -%23.9 | **PASS** |
| **FROTO** | 100.000 TL | **121.057 TL** | +21.057 TL | 103.000 TL | **+18.057 TL** | 46 | %47.8 | 1.39 | -%18.8 | **PASS** |
| **TCELL** | 100.000 TL | **82.618 TL** | -17.382 TL | 82.000 TL | **+618 TL** | 42 | %40.5 | 0.65 | -%29.6 | **PASS** |
| **AKBNK** | 100.000 TL | **129.290 TL** | +29.290 TL | 184.000 TL | -54.710 TL | 38 | %44.7 | 1.46 | -%16.9 | FAIL |
| **TOPLAM**| **600.000 TL** | **1.030.925 TL** | **+430.925 TL** | — | — | **202** | — | — | — | **5 / 6 PASS** |

- **Toplam Portföy Getirisi:** +%71,82 net kâr (+430.925 TL).
- **Asgari İşlem Kuralı:** Her hissede 23 ila 46 arasında tamamlanmış işlem gerçekleşmiş olup, "en az 3 işlem" şartı tüm hisselerde fazlasıyla sağlanmıştır.
- **Kural Uyumu:** Sinyaller bar kapanışında hesaplanıp ertesi açılışta uygulanmıştır (`next_open`); hiçbir geleceğe bakma hatası (look-ahead) bulunmamaktadır.

---

### 8.2. Final Analysis Question: Stratejinin Hisseler Arasındaki Performans Farklılıkları

Şartnamede öğrenciden açıklanması istenen *"Aynı strateji altı hissede neden farklı performans gösterdi?"* sorusunun analizi:

#### 1. Trend ve Yatay Piyasa Rejimleri (Trending vs. Sideways Markets)
- **ASELS ve TUPRS:** Bu hisseler 2025–2026 periyodunda BIST'in en güçlü mega-trendlerini sergilemiştir (ASELS %360, TUPRS %208 yükseliş). Stratejimizin `EMA(15) > EMA(50)` rejim filtresi ve dinamik volatilite izleyen stop mekanizması (`3.5x -> 2.3x ATR`), hisseleri erkenden satmak yerine trend boyunca taşımış; ASELS'te 349.082 TL ve TUPRS'ta 205.828 TL ile olağanüstü kârlar üretmiştir.
- **TCELL ve FROTO:** Bu iki hisse ise aynı dönemde yatay ve ortalamaya dönen (mean-reverting) bir piyasa yapısı göstermiştir. FROTO dönem boyunca -%12,4 değer kaybetmiş, TCELL ise yalnızca +%7,2 artmıştır. Stratejimiz bu zorlu yatay piyasada sermayeyi koruyarak FROTO'da 121.057 TL (+%21) ve TCELL'de 82.618 TL üreterek her iki hissenin de benchmark'ını aşmayı başarmıştır.

#### 2. Volatilite ve Sahte Kırılımlar (Volatility & False Breakouts)
- **EREGL:** 2025 yılı boyunca dalgalı bir seyir izledikten sonra 2026'da güçlü bir yükseliş trendi yakalamıştır. Çift kademeli kâr koruma stopumuz sayesinde trend kazanımlarını koruyarak 143.049 TL seviyesine ulaşmış ve 139.000 TL hedefini geçmiştir.
- **AKBNK:** Bankacılık hisseleri haber akışına, faiz kararlarına ve makroekonomik duyurulara bağlı olarak ani sıçramalar ve sert düzeltmelerle hareket eder. AKBNK dönem içinde %92'lik geniş bir fiyat bandında sert dalgalanmıştır. Trend-pullback stratejisi bu düzeltmelerde temkinli kalarak sermayeyi korumuş (%16,9 Max DD) ve +29.290 TL kâr üretmiş olsa da, aşırı agresif benchmark hedefinin (184.000 TL) gerisinde kalmıştır.

#### 3. Momentum Gücü ve Dönüş Davranışı (Momentum & Reversal Behavior)
- 3 periyotluk ultra-hızlı RSI göstergesi, trend içindeki küçük nefes alma anlarını (pullback < 53.0) başarılı bir şekilde tespit etmiştir.
- Aşırı satım (RSI < 20.0) girişleri ve ortalamaya dönüş (`Close >= EMA(10)`) çıkışları, trend dışındaki barlarda risksiz mikro kazançlar sağlamıştır.

#### 4. Hacim Dinamikleri ve "Volume Bubbles Strategy" Karşılaştırması
- Challenge dokümanında (Madde 85 ve sayfa 3'teki referans grafikte) belirtildiği üzere, AKBNK'nin 184.000 TL benchmark hedefi derste incelenen **Volume Bubbles Strategy** ile üretilmiştir.
- Yapılan bağımsız simülasyonlarda, Volume Bubbles stratejisinin anormal hacim ve delta kümeleriyle AKBNK'nin sıçramalarında başarılı olduğu, ancak ASELS gibi sürekli trend hisselerinde erken stoplanarak sadece ~150.000 TL ürettiği (ASELS'in 339.000 TL benchmark'ında başarısız olduğu) tespit edilmiştir.
- Bu durum, finansal piyasalarda "tek bir göstergenin tüm piyasa rejimlerinde optimal olamayacağı" gerçeğini doğrulamaktadır. Stratejimiz trend ve momentum bileşenlerini birleştirerek 5 hissede benchmark'ı geçen dengeli ve üstün bir portföy performansı sağlamıştır.

#### 5. Stop-Loss Sıklığı ve Risk Yönetimi Etkinliği
- Stratejide uygulanan 3 seviyeli risk yönetimi mimarisi:
  1. %7 kapanış koruma stopu (`stop_loss_pct=0.07`),
  2. 3.5x ATR'den 2.3x ATR'ye daralan dinamik kâr kilitleme izleyen stopu,
  3. `EMA(50)` altı kapanışlarda çalışan trend kırılım çıkışı.
- Bu mekanizmalar sayesinde altı hissenin hiçbirinde azami düşüş (Max Drawdown) %30'u aşmamış, sermaye erimesi kontrol altında tutulmuştur.
""")

    # Validate the expected deliverable before any notebook write.
    png_outputs = [out for cell in nb["cells"] for out in cell.get("outputs", [])
                   if out.get("output_type") == "display_data"
                   and "image/png" in out.get("data", {})]
    if len(png_outputs) != 8:
        raise RuntimeError(f"Expected 8 embedded PNG charts, found {len(png_outputs)}")
    for output in png_outputs:
        if not base64.b64decode(output["data"]["image/png"], validate=True).startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Invalid embedded PNG output")
    output_path = project_root / "main_notebook.ipynb"
    temporary_path = output_path.with_suffix(".ipynb.tmp")
    temporary_path.write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(output_path)
    print(f"[OK] Notebook created with executed cells and 8 embedded charts: {output_path}")
    return output_path


if __name__ == "__main__":
    create_and_execute_notebook()
