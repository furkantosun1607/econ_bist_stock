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

Strateji, hisse adına veya belirli takvim günlerine göre karar vermez.

- **Isınma:** En az 60 bar gözlem biriktikten sonra kapanış sinyali üretilebilir;
  ilk olası gerçekleşme 61. barın açılışıdır.
- **Trend rejimi:** `EMA20 > EMA60` ve `Close > EMA60` birlikte sağlanır.
- **Giriş:** Pozisyon yokken `(trend ve RSI3 < 50) veya RSI3 < 20`.
  Böylece trend içindeki geri çekilmeler ve diğer rejimlerde aşırı satış aranır.
- **Toparlanma çıkışı:** Trend koşulu sağlanmıyorsa
  `(RSI3 > 70) veya (Close >= EMA10)`. Trend devam ederken bu çıkış kullanılmaz.
- **Risk:** Giriş açılışı ve sonraki kapanışların en yükseğinden güncel
  `5 × ATR14` çıkarılır; `Close < bu seviye` kapanışta çıkış sinyali üretir.
  Çıkış ertesi açılıştadır; stop fiyatından
  kesin gerçekleşme varsayılmaz ve gece oluşabilecek boşluk riski kalır.

Kesin eşitsizlikler ve geçişler `strategies/adaptive_regime.py` içindedir.
Aşağıdaki hücre kullanılan tüm parametreleri kaydeder. Kurallar tüm hisselerde
aynıdır; bu notebook herhangi bir parametre araması yapmaz.
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

    md("""## 8. Sonuçları değerlendirme

Her hisse için sermaye hedefi ve üç işlem şartı birlikte kontrol edilmelidir.
Veri kapsamı eksikken görülen benchmark karşılaştırmaları yalnızca mevcut
örneklem içindir. Bir hisse veya dönem iyi sonuç verirken diğerleri kaybedebilir:
trend takibi uzun yönlü hareketleri korumayı, kısa RSI işlemleri yatay piyasada
toparlanmayı yakalamayı amaçlar; güçlü düşüşte geri çekilme girişleri zarar edebilir.

Seçim yaparken yalnızca toplam kârı değil, 2026 alt dönemlerindeki dayanıklılığı,
al-tuta göre farkı, azami düşüşü ve maliyet etkisini birlikte inceleyin. Eksik
1 Ekim verisi doğrulanmadan tam dönem challenge başarısı ilan edilemez.

**Bu dondurulmuş model challenge'ı çözmüş değildir.** Mevcut 440 bar üzerinde
yalnızca 3/6 hisse hedef/işlem şartını sağlar; 600.000 TL toplam sermaye yaklaşık
913.200 TL olur. AKBNK'da tam dönem azami düşüş yaklaşık %50,68 ve 2026 getirisi
yaklaşık -%32,79'dur. Bu zayıflıklar raporlanır; 2026 sonucu görüldükten sonra
model yeniden ayarlanarak bağımsız doğrulama iddiasında bulunulmaz.
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
