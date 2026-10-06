"""
BIST Algorithmic Trading Challenge - Data Loader
=================================================
yfinance ile BIST hisse verilerini çeker, CSV olarak cache'ler,
temizlik ve doğrulama yapar.

Kullanım:
    from data_loader import load_stock_data, load_all_stocks

    # Tek hisse
    df = load_stock_data("AKBNK.IS")

    # Tüm hisseler
    all_data = load_all_stocks()  # dict[str, pd.DataFrame]
"""

import pandas as pd
import yfinance as yf
from pathlib import Path

from config import (
    STOCKS,
    START_DATE,
    END_DATE,
    DATA_DIR,
    get_short_name,
)


def _get_cache_path(ticker: str) -> Path:
    """Cache dosya yolunu döner."""
    name = get_short_name(ticker)
    return DATA_DIR / f"{name}_ohlcv.csv"


def _download_from_yfinance(ticker: str) -> pd.DataFrame:
    """
    yfinance'den OHLCV verisini indirir.
    
    Returns:
        Temiz DataFrame: Date (index), Open, High, Low, Close, Volume
    """
    print(f"  [DL] {get_short_name(ticker)} verisi yfinance'den indiriliyor...")
    
    df = yf.download(
        ticker,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=True,   # Adjusted close kullan
        progress=False,
    )
    
    if df.empty:
        raise ValueError(
            f"{ticker} için veri indirilemedi. "
            f"Ticker doğru mu? İnternet bağlantısı var mı?"
        )
    
    # yfinance bazen MultiIndex döner, düzelt
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Sadece OHLCV kolonlarını al
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"{ticker} verisinde '{col}' kolonu bulunamadı.")
    
    df = df[required_cols].copy()
    
    # Index adını düzelt
    df.index.name = "Date"
    
    return df


def _clean_data(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Veri temizliği ve doğrulama.
    
    - NaN satırları kaldır
    - Negatif fiyat kontrolü
    - Tarih sıralama
    - Duplicate tarih kontrolü
    """
    name = get_short_name(ticker)
    original_len = len(df)
    
    # NaN kaldır
    df = df.dropna()
    dropped = original_len - len(df)
    if dropped > 0:
        print(f"  [!] {name}: {dropped} NaN satir kaldirildi")
    
    # Tarih sırala
    df = df.sort_index()
    
    # Duplicate tarihleri kaldır
    dup_count = df.index.duplicated().sum()
    if dup_count > 0:
        df = df[~df.index.duplicated(keep="first")]
        print(f"  [!] {name}: {dup_count} duplicate tarih kaldirildi")
    
    # Negatif fiyat kontrolü
    price_cols = ["Open", "High", "Low", "Close"]
    for col in price_cols:
        if (df[col] <= 0).any():
            bad_count = (df[col] <= 0).sum()
            print(f"  [!] {name}: {col} kolonunda {bad_count} negatif/sifir deger!")
    
    return df


def _print_data_summary(df: pd.DataFrame, ticker: str):
    """Veri özeti yazdır."""
    name = get_short_name(ticker)
    print(f"  [OK] {name}: {len(df)} gun | "
          f"{df.index[0].strftime('%Y-%m-%d')} -> {df.index[-1].strftime('%Y-%m-%d')} | "
          f"Fiyat: {df['Close'].iloc[0]:.2f} -> {df['Close'].iloc[-1]:.2f} TL")


def load_stock_data(
    ticker: str,
    use_cache: bool = True,
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Tek bir hisse için OHLCV verisini yükler.
    
    Args:
        ticker: yfinance ticker (ör. "AKBNK.IS")
        use_cache: True ise önce cache'e bak
        force_download: True ise cache'i yoksay, yeniden indir
    
    Returns:
        pd.DataFrame: Date (index), Open, High, Low, Close, Volume
    """
    cache_path = _get_cache_path(ticker)
    
    # Cache'den oku
    if use_cache and not force_download and cache_path.exists():
        df = pd.read_csv(cache_path, index_col="Date", parse_dates=True)
        _print_data_summary(df, ticker)
        return df
    
    # yfinance'den indir
    df = _download_from_yfinance(ticker)
    
    # Temizle
    df = _clean_data(df, ticker)
    
    # Cache'e kaydet
    if use_cache:
        df.to_csv(cache_path)
    
    _print_data_summary(df, ticker)
    return df


def load_all_stocks(
    use_cache: bool = True,
    force_download: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Tüm hisseler için OHLCV verilerini yükler.
    
    Args:
        use_cache: True ise önce cache'e bak
        force_download: True ise cache'i yoksay, yeniden indir
    
    Returns:
        dict[str, pd.DataFrame]: ticker → DataFrame mapping
    """
    print("=" * 60)
    print("Veri Yükleme")
    print("=" * 60)
    
    all_data = {}
    failed = []
    
    for ticker in STOCKS:
        try:
            df = load_stock_data(ticker, use_cache, force_download)
            all_data[ticker] = df
        except Exception as e:
            name = get_short_name(ticker)
            print(f"  [FAIL] {name}: HATA - {e}")
            failed.append(ticker)
    
    print(f"\n  Basarili: {len(all_data)}/{len(STOCKS)}")
    if failed:
        print(f"  Basarisiz: {', '.join(get_short_name(t) for t in failed)}")
    print("=" * 60)
    
    return all_data


def get_price_change_summary(all_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Tüm hisselerin fiyat değişim özetini tablo olarak döner.
    Veriyi doğrulamak ve ilk analiz için kullanılır.
    """
    rows = []
    for ticker, df in all_data.items():
        first_close = df["Close"].iloc[0]
        last_close = df["Close"].iloc[-1]
        change_pct = ((last_close - first_close) / first_close) * 100
        volatility = df["Close"].pct_change().std() * 100
        avg_volume = df["Volume"].mean()
        
        rows.append({
            "Hisse": get_short_name(ticker),
            "İlk Fiyat": round(first_close, 2),
            "Son Fiyat": round(last_close, 2),
            "Değişim (%)": round(change_pct, 2),
            "Günlük Vol. (%)": round(volatility, 2),
            "Ort. Hacim": int(avg_volume),
            "Gün Sayısı": len(df),
        })
    
    return pd.DataFrame(rows)


# ============================================================
# Doğrudan çalıştırılırsa: tüm verileri indir ve özetle
# ============================================================
if __name__ == "__main__":
    all_data = load_all_stocks(use_cache=True)
    
    if all_data:
        print("\n")
        summary = get_price_change_summary(all_data)
        print(summary.to_string(index=False))
