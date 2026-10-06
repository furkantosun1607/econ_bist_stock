"""
BIST Algorithmic Trading Challenge - Configuration
===================================================
Tüm proje sabitleri, hisse listesi, benchmark hedefleri ve yol tanımları.
Diğer modüller bu dosyadan import eder.
"""

import os
from pathlib import Path

# ============================================================
# Proje Yolları
# ============================================================
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
TRADES_DIR = RESULTS_DIR / "trades"
CHARTS_DIR = RESULTS_DIR / "charts"

# Dizinleri oluştur (yoksa)
for d in [DATA_DIR, RESULTS_DIR, TRADES_DIR, CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# Hisse Sembolleri (yfinance formatı: .IS = Istanbul)
# ============================================================
STOCKS = [
    "AKBNK.IS",
    "ASELS.IS",
    "TUPRS.IS",
    "TCELL.IS",
    "FROTO.IS",
    "EREGL.IS",
]

# Kısa isim mapping (raporlama ve dosya isimlendirme için)
STOCK_NAMES = {
    "AKBNK.IS": "AKBNK",
    "ASELS.IS": "ASELS",
    "TUPRS.IS": "TUPRS",
    "TCELL.IS": "TCELL",
    "FROTO.IS": "FROTO",
    "EREGL.IS": "EREGL",
}

# ============================================================
# Backtest Parametreleri
# ============================================================
START_DATE = "2025-01-01"
END_DATE = "2026-10-01"
INITIAL_CAPITAL = 100_000  # TL

# ============================================================
# Benchmark Hedefleri (Her hisse bireysel olarak geçilmeli)
# ============================================================
BENCHMARKS = {
    "AKBNK.IS": {
        "net_profit": 84_000,
        "final_capital": 184_000,
    },
    "ASELS.IS": {
        "net_profit": 239_000,
        "final_capital": 339_000,
    },
    "TUPRS.IS": {
        "net_profit": 72_000,
        "final_capital": 172_000,
    },
    "TCELL.IS": {
        "net_profit": -18_000,
        "final_capital": 82_000,
    },
    "FROTO.IS": {
        "net_profit": 3_000,
        "final_capital": 103_000,
    },
    "EREGL.IS": {
        "net_profit": 39_000,
        "final_capital": 139_000,
    },
}

# ============================================================
# Trade Parametreleri (varsayılan, strateji override edebilir)
# ============================================================
COMMISSION_RATE = 0.0  # Komisyon oranı (0 = komisyon yok)
SLIPPAGE_RATE = 0.0    # Slippage oranı (0 = slippage yok)

# ============================================================
# Yardımcı Fonksiyonlar
# ============================================================

def get_short_name(ticker: str) -> str:
    """yfinance ticker'ından kısa hisse adını döner."""
    return STOCK_NAMES.get(ticker, ticker.replace(".IS", ""))


def get_benchmark(ticker: str) -> dict:
    """Bir hissenin benchmark bilgilerini döner."""
    return BENCHMARKS.get(ticker, {})


def print_config():
    """Mevcut konfigürasyonu yazdırır (debug/doğrulama için)."""
    print("=" * 60)
    print("BIST Algorithmic Trading Challenge - Configuration")
    print("=" * 60)
    print(f"  Backtest Period : {START_DATE} -> {END_DATE}")
    print(f"  Initial Capital : {INITIAL_CAPITAL:,.0f} TL")
    print(f"  Stocks          : {', '.join(get_short_name(s) for s in STOCKS)}")
    print(f"  Commission      : {COMMISSION_RATE*100:.2f}%")
    print(f"  Slippage        : {SLIPPAGE_RATE*100:.2f}%")
    print()
    print("  Benchmark Targets:")
    for ticker in STOCKS:
        bm = BENCHMARKS[ticker]
        name = get_short_name(ticker)
        print(f"    {name:6s} -> Final Capital > {bm['final_capital']:>10,.0f} TL  "
              f"(Net Profit > {bm['net_profit']:>+10,.0f} TL)")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
