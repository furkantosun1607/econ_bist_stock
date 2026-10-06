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

import hashlib
import warnings

import numpy as np
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
        # yfinance's end is exclusive; the assignment's final date is inclusive.
        end=(pd.Timestamp(END_DATE) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
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
    - Gecersiz OHLCV degerlerini reddet
    - Tarih sıralama
    - Duplicate tarih kontrolü
    """
    name = get_short_name(ticker)
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = set(required_cols).difference(df.columns)
    if missing:
        raise ValueError(f"{ticker}: missing OHLCV columns: {sorted(missing)}")
    df = df[required_cols].copy()
    try:
        df.index = pd.DatetimeIndex(pd.to_datetime(df.index, errors="raise"))
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df[required_cols] = df[required_cols].apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{ticker}: invalid dates or non-numeric OHLCV data") from exc
    if df.index.hasnans:
        raise ValueError(f"{ticker}: missing dates")
    df.index.name = "Date"
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
    
    # A cache may have been collected for a different requested interval.
    df = df.loc[(df.index >= pd.Timestamp(START_DATE)) &
                (df.index <= pd.Timestamp(END_DATE))].copy()
    if df.empty:
        raise ValueError(f"{ticker}: no usable OHLCV rows in the requested interval")

    # Reject corrupted inputs rather than allowing impossible fills in a backtest.
    price_cols = ["Open", "High", "Low", "Close"]
    if not np.isfinite(df[required_cols].to_numpy(dtype=float)).all():
        raise ValueError(f"{ticker}: non-finite OHLCV values")
    if (df[price_cols] <= 0).any().any() or (df["Volume"] < 0).any():
        raise ValueError(f"{ticker}: prices must be positive and volume non-negative")
    invalid_range = ((df["High"] < df[["Open", "Low", "Close"]].max(axis=1)) |
                     (df["Low"] > df[["Open", "High", "Close"]].min(axis=1)))
    if invalid_range.any():
        raise ValueError(f"{ticker}: inconsistent OHLC price ranges")
    
    return df


def _annotate_data(df: pd.DataFrame, source: str, cache_path: Path | None = None):
    """Expose actual coverage and provenance without inventing missing prices."""
    coverage = {
        "requested_start": START_DATE,
        "requested_end_inclusive": END_DATE,
        "actual_start": df.index[0].strftime("%Y-%m-%d"),
        "actual_end": df.index[-1].strftime("%Y-%m-%d"),
        "rows": len(df),
        "end_date_observed": pd.Timestamp(END_DATE) in df.index,
    }
    df.attrs["data_coverage"] = coverage
    df.attrs["data_provenance"] = {
        "source": source,
        "independently_verified": False,
        "sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest()
        if cache_path is not None else None,
    }
    if df.index[-1] < pd.Timestamp(END_DATE):
        warnings.warn(
            f"Data ends on {coverage['actual_end']}; requested inclusive end is "
            f"{END_DATE}. Full-period coverage has not been verified. "
            "No missing bars were filled or downloaded automatically.",
            UserWarning,
            stacklevel=3,
        )


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
        df = _clean_data(df, ticker)
        _annotate_data(df, source="local_cache_unverified", cache_path=cache_path)
        _print_data_summary(df, ticker)
        return df
    
    # yfinance'den indir
    df = _download_from_yfinance(ticker)
    
    # Temizle
    df = _clean_data(df, ticker)
    
    # Cache'e kaydet
    if use_cache:
        df.to_csv(cache_path)
    _annotate_data(df, source="yfinance_auto_adjust",
                   cache_path=cache_path if use_cache else None)
    
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
