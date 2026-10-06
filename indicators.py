"""
BIST Algorithmic Trading Challenge - Technical Indicators Library
=================================================================
Stratejilerin kullanabileceği tüm teknik indikatorler.
Her indikator bagimsiz bir fonksiyon olarak yazilmistir.
Strateji sadece ihtiyac duydugunu cagirir.

Kullanim:
    from indicators import add_sma, add_rsi, add_all_indicators

    # Tek indikator ekle
    df = add_sma(df, period=20)

    # Tum indikatorleri ekle (varsayilan parametrelerle)
    df = add_all_indicators(df)
"""

import numpy as np
import pandas as pd


# ============================================================
# TREND INDICATORS
# ============================================================

def add_sma(df: pd.DataFrame, period: int = 20, col: str = "Close") -> pd.DataFrame:
    """
    Simple Moving Average (Basit Hareketli Ortalama).
    
    Args:
        df: OHLCV DataFrame
        period: Pencere boyutu
        col: Hesaplanacak kolon
    
    Eklenen kolon: SMA_{period}
    """
    df[f"SMA_{period}"] = df[col].rolling(window=period).mean()
    return df


def add_ema(df: pd.DataFrame, period: int = 20, col: str = "Close") -> pd.DataFrame:
    """
    Exponential Moving Average (Ustel Hareketli Ortalama).
    
    Args:
        df: OHLCV DataFrame
        period: Pencere boyutu
        col: Hesaplanacak kolon
    
    Eklenen kolon: EMA_{period}
    """
    df[f"EMA_{period}"] = df[col].ewm(span=period, adjust=False).mean()
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    col: str = "Close",
) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence.
    
    Eklenen kolonlar: MACD, MACD_Signal, MACD_Hist
    """
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    
    return df


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Average Directional Index - Trend gucu olcumu.
    
    Eklenen kolonlar: ADX, Plus_DI, Minus_DI
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # Smoothed values (Wilder's smoothing)
    atr = pd.Series(tr, index=df.index).rolling(window=period).mean()
    plus_di_raw = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    minus_di_raw = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
    
    # DI values
    df["Plus_DI"] = 100 * (plus_di_raw / atr)
    df["Minus_DI"] = 100 * (minus_di_raw / atr)
    
    # DX and ADX
    di_sum = df["Plus_DI"] + df["Minus_DI"]
    di_diff = (df["Plus_DI"] - df["Minus_DI"]).abs()
    dx = 100 * (di_diff / di_sum.replace(0, np.nan))
    
    df["ADX"] = dx.rolling(window=period).mean()
    
    return df


# ============================================================
# MOMENTUM / OSCILLATOR INDICATORS
# ============================================================

def add_rsi(df: pd.DataFrame, period: int = 14, col: str = "Close") -> pd.DataFrame:
    """
    Relative Strength Index.
    
    Eklenen kolon: RSI_{period}
    """
    delta = df[col].diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    # Wilder's smoothing (EMA)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))
    
    return df


def add_stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """
    Stochastic Oscillator (%K ve %D).
    
    Eklenen kolonlar: Stoch_K, Stoch_D
    """
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    
    denom = high_max - low_min
    df["Stoch_K"] = 100 * ((df["Close"] - low_min) / denom.replace(0, np.nan))
    df["Stoch_D"] = df["Stoch_K"].rolling(window=d_period).mean()
    
    return df


def add_momentum(df: pd.DataFrame, period: int = 10, col: str = "Close") -> pd.DataFrame:
    """
    Price Momentum (Fiyat degisim orani).
    
    Eklenen kolon: Momentum_{period}
    """
    df[f"Momentum_{period}"] = df[col].pct_change(periods=period) * 100
    return df


def add_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Commodity Channel Index.
    
    Eklenen kolon: CCI_{period}
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = typical_price.rolling(window=period).mean()
    mad = typical_price.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    df[f"CCI_{period}"] = (typical_price - sma_tp) / (0.015 * mad.replace(0, np.nan))
    return df


def add_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Williams %R.
    
    Eklenen kolon: Williams_R_{period}
    """
    high_max = df["High"].rolling(window=period).max()
    low_min = df["Low"].rolling(window=period).min()
    denom = high_max - low_min
    df[f"Williams_R_{period}"] = -100 * ((high_max - df["Close"]) / denom.replace(0, np.nan))
    return df


# ============================================================
# VOLATILITY INDICATORS
# ============================================================

def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Average True Range - Volatilite olcumu.
    
    Eklenen kolon: ATR_{period}
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df[f"ATR_{period}"] = tr.rolling(window=period).mean()
    
    return df


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    col: str = "Close",
) -> pd.DataFrame:
    """
    Bollinger Bands.
    
    Eklenen kolonlar: BB_Upper, BB_Middle, BB_Lower, BB_Width, BB_Position
    """
    sma = df[col].rolling(window=period).mean()
    std = df[col].rolling(window=period).std()
    
    df["BB_Upper"] = sma + (std_dev * std)
    df["BB_Middle"] = sma
    df["BB_Lower"] = sma - (std_dev * std)
    
    # Bant genisligi (normalize)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]
    
    # Fiyatin bant icindeki pozisyonu (0=alt, 1=ust)
    band_range = df["BB_Upper"] - df["BB_Lower"]
    df["BB_Position"] = (df[col] - df["BB_Lower"]) / band_range.replace(0, np.nan)
    
    return df


def add_keltner_channels(
    df: pd.DataFrame,
    ema_period: int = 20,
    atr_period: int = 14,
    atr_multiplier: float = 2.0,
) -> pd.DataFrame:
    """
    Keltner Channels.
    
    Eklenen kolonlar: KC_Upper, KC_Middle, KC_Lower
    """
    # EMA ortasi
    df["KC_Middle"] = df["Close"].ewm(span=ema_period, adjust=False).mean()
    
    # ATR hesapla (gecici)
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()
    
    df["KC_Upper"] = df["KC_Middle"] + (atr_multiplier * atr)
    df["KC_Lower"] = df["KC_Middle"] - (atr_multiplier * atr)
    
    return df


# ============================================================
# VOLUME INDICATORS
# ============================================================

def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Volume Simple Moving Average.
    
    Eklenen kolonlar: Volume_SMA_{period}, Volume_Ratio
    """
    df[f"Volume_SMA_{period}"] = df["Volume"].rolling(window=period).mean()
    df["Volume_Ratio"] = df["Volume"] / df[f"Volume_SMA_{period}"]
    return df


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    On-Balance Volume.
    
    Eklenen kolon: OBV
    """
    direction = np.sign(df["Close"].diff())
    df["OBV"] = (direction * df["Volume"]).cumsum()
    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volume Weighted Average Price (gunluk kumulatif).
    
    Eklenen kolon: VWAP
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()
    cumulative_vol = df["Volume"].cumsum()
    df["VWAP"] = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
    return df


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def add_support_resistance(
    df: pd.DataFrame,
    lookback: int = 20,
) -> pd.DataFrame:
    """
    Rolling Support ve Resistance seviyeleri.
    
    Eklenen kolonlar: Support, Resistance
    """
    df["Support"] = df["Low"].rolling(window=lookback).min()
    df["Resistance"] = df["High"].rolling(window=lookback).max()
    return df


def add_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot Points (onceki gunun OHLC'sine gore).
    
    Eklenen kolonlar: Pivot, Pivot_S1, Pivot_S2, Pivot_R1, Pivot_R2
    """
    prev_high = df["High"].shift(1)
    prev_low = df["Low"].shift(1)
    prev_close = df["Close"].shift(1)
    
    pivot = (prev_high + prev_low + prev_close) / 3
    
    df["Pivot"] = pivot
    df["Pivot_S1"] = (2 * pivot) - prev_high
    df["Pivot_S2"] = pivot - (prev_high - prev_low)
    df["Pivot_R1"] = (2 * pivot) - prev_low
    df["Pivot_R2"] = pivot + (prev_high - prev_low)
    
    return df


# ============================================================
# PRICE ACTION / DERIVED
# ============================================================

def add_daily_returns(df: pd.DataFrame, col: str = "Close") -> pd.DataFrame:
    """
    Gunluk getiri yuzdeleri.
    
    Eklenen kolon: Daily_Return
    """
    df["Daily_Return"] = df[col].pct_change() * 100
    return df


def add_price_channels(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Donchian Price Channels.
    
    Eklenen kolonlar: Channel_High, Channel_Low, Channel_Mid
    """
    df["Channel_High"] = df["High"].rolling(window=period).max()
    df["Channel_Low"] = df["Low"].rolling(window=period).min()
    df["Channel_Mid"] = (df["Channel_High"] + df["Channel_Low"]) / 2
    return df


def add_candle_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mum cubugu ozellikleri.
    
    Eklenen kolonlar: Body_Size, Upper_Shadow, Lower_Shadow, Is_Bullish
    """
    body = df["Close"] - df["Open"]
    df["Body_Size"] = body.abs()
    df["Upper_Shadow"] = df["High"] - pd.concat([df["Open"], df["Close"]], axis=1).max(axis=1)
    df["Lower_Shadow"] = pd.concat([df["Open"], df["Close"]], axis=1).min(axis=1) - df["Low"]
    df["Is_Bullish"] = (body > 0).astype(int)
    return df


# ============================================================
# COMPOSITE / UTILITY
# ============================================================

def add_all_indicators(
    df: pd.DataFrame,
    sma_periods: list[int] | None = None,
    ema_periods: list[int] | None = None,
    rsi_period: int = 14,
    atr_period: int = 14,
    bb_period: int = 20,
    macd_params: tuple[int, int, int] | None = None,
    volume_sma_period: int = 20,
    adx_period: int = 14,
    stoch_params: tuple[int, int] | None = None,
    sr_lookback: int = 20,
) -> pd.DataFrame:
    """
    Tum indikatorleri varsayilan parametrelerle ekler.
    Strateji icin hizli baslangic.
    
    Args:
        df: OHLCV DataFrame
        sma_periods: SMA periyotlari listesi (varsayilan: [10, 20, 50])
        ema_periods: EMA periyotlari listesi (varsayilan: [10, 20, 50])
        rsi_period: RSI periyodu
        atr_period: ATR periyodu
        bb_period: Bollinger Bands periyodu
        macd_params: (fast, slow, signal) tuple
        volume_sma_period: Hacim SMA periyodu
        adx_period: ADX periyodu
        stoch_params: (k_period, d_period) tuple
        sr_lookback: Support/Resistance lookback
    
    Returns:
        Tum indikatorler eklenmis DataFrame
    """
    if sma_periods is None:
        sma_periods = [10, 20, 50]
    if ema_periods is None:
        ema_periods = [10, 20, 50]
    if macd_params is None:
        macd_params = (12, 26, 9)
    if stoch_params is None:
        stoch_params = (14, 3)
    
    # Trend
    for p in sma_periods:
        df = add_sma(df, period=p)
    for p in ema_periods:
        df = add_ema(df, period=p)
    df = add_macd(df, fast=macd_params[0], slow=macd_params[1], signal=macd_params[2])
    df = add_adx(df, period=adx_period)
    
    # Momentum
    df = add_rsi(df, period=rsi_period)
    df = add_stochastic(df, k_period=stoch_params[0], d_period=stoch_params[1])
    df = add_momentum(df, period=10)
    
    # Volatility
    df = add_atr(df, period=atr_period)
    df = add_bollinger_bands(df, period=bb_period)
    
    # Volume
    df = add_volume_sma(df, period=volume_sma_period)
    df = add_obv(df)
    
    # Support/Resistance
    df = add_support_resistance(df, lookback=sr_lookback)
    
    # Price Action
    df = add_daily_returns(df)
    df = add_candle_features(df)
    
    return df


def list_available_indicators() -> list[str]:
    """Mevcut tum indikator fonksiyonlarini listeler."""
    indicators = [
        "add_sma(period)         - Simple Moving Average",
        "add_ema(period)         - Exponential Moving Average",
        "add_macd(fast,slow,sig) - MACD",
        "add_adx(period)         - Average Directional Index",
        "add_rsi(period)         - Relative Strength Index",
        "add_stochastic(k,d)     - Stochastic Oscillator",
        "add_momentum(period)    - Price Momentum",
        "add_cci(period)         - Commodity Channel Index",
        "add_williams_r(period)  - Williams %R",
        "add_atr(period)         - Average True Range",
        "add_bollinger_bands(p)  - Bollinger Bands",
        "add_keltner_channels()  - Keltner Channels",
        "add_volume_sma(period)  - Volume Moving Average",
        "add_obv()               - On-Balance Volume",
        "add_vwap()              - Volume Weighted Avg Price",
        "add_support_resistance()- Support & Resistance",
        "add_pivot_points()      - Pivot Points",
        "add_daily_returns()     - Daily Returns",
        "add_price_channels(p)   - Donchian Channels",
        "add_candle_features()   - Candlestick Features",
        "add_all_indicators()    - All indicators at once",
    ]
    return indicators


# ============================================================
# Test / Demo
# ============================================================
if __name__ == "__main__":
    from data_loader import load_stock_data
    from config import get_short_name
    
    print("=" * 60)
    print("Indicator Library - Test")
    print("=" * 60)
    
    # AKBNK ile test
    ticker = "AKBNK.IS"
    df = load_stock_data(ticker)
    
    print(f"\n  Veri boyutu (ham): {df.shape}")
    
    # Tum indikatorleri ekle
    df = add_all_indicators(df)
    
    print(f"  Veri boyutu (indikatorlerle): {df.shape}")
    print(f"  Eklenen kolonlar ({df.shape[1] - 5} indikator):")
    
    indicator_cols = [c for c in df.columns if c not in ["Open", "High", "Low", "Close", "Volume"]]
    for i, col in enumerate(indicator_cols, 1):
        nan_count = df[col].isna().sum()
        print(f"    {i:2d}. {col:25s} - NaN: {nan_count:3d} | "
              f"Son deger: {df[col].iloc[-1]:>12.2f}")
    
    print(f"\n  NaN olmayan satir sayisi: {df.dropna().shape[0]} / {len(df)}")
    print("=" * 60)
