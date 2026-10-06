"""
SMA Crossover Strategy (Test / Ornek Strateji)
===============================================
Kisa SMA uzun SMA'yi yukari keserse BUY,
asagi keserse SELL sinyali uretir.

Bu strateji backtest motorunu test etmek icin yazilmistir.
Gercek yarisma stratejisi degil, sadece altyapi dogrulamasi.

Kullanim:
    from strategies.sma_crossover import SmaCrossoverStrategy
    
    strategy = SmaCrossoverStrategy(fast_period=10, slow_period=50)
    df = strategy.run(df)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from strategy_base import StrategyBase
from indicators import add_sma


class SmaCrossoverStrategy(StrategyBase):
    """
    Simple Moving Average Crossover Strategy.
    
    Parametreler:
        fast_period (int): Kisa SMA periyodu (varsayilan: 10)
        slow_period (int): Uzun SMA periyodu (varsayilan: 50)
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 50):
        super().__init__(
            name="SMA_Crossover",
            params={"fast_period": fast_period, "slow_period": slow_period},
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Gerekli SMA'lari ekle."""
        df = df.copy()
        df = add_sma(df, period=self.fast_period)
        df = add_sma(df, period=self.slow_period)
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        SMA Crossover sinyalleri:
        - BUY (1):  Kisa SMA, uzun SMA'yi yukari keser
        - SELL (-1): Kisa SMA, uzun SMA'yi asagi keser
        - HOLD (0): Diger durumlar
        """
        fast_col = f"SMA_{self.fast_period}"
        slow_col = f"SMA_{self.slow_period}"
        
        # Baslangicta tum sinyaller HOLD
        df["Signal"] = 0
        
        # Crossover tespit
        # Onceki bar: fast < slow, su anki bar: fast >= slow -> BUY
        # Onceki bar: fast >= slow, su anki bar: fast < slow -> SELL
        fast = df[fast_col]
        slow = df[slow_col]
        
        prev_fast = fast.shift(1)
        prev_slow = slow.shift(1)
        
        # Golden Cross (BUY): fast onceden slow'un altindaydi, simdi ustune gecti
        buy_signal = (prev_fast < prev_slow) & (fast >= slow)
        
        # Death Cross (SELL): fast onceden slow'un ustundeydi, simdi altina gecti
        sell_signal = (prev_fast >= prev_slow) & (fast < slow)
        
        df.loc[buy_signal, "Signal"] = 1
        df.loc[sell_signal, "Signal"] = -1
        
        # NaN olan satirlarda sinyal uretme
        nan_mask = df[fast_col].isna() | df[slow_col].isna()
        df.loc[nan_mask, "Signal"] = 0
        
        # Signal kolonunu int'e cevir
        df["Signal"] = df["Signal"].astype(int)
        
        return df


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    from data_loader import load_stock_data
    from config import STOCKS, get_short_name
    
    print("=" * 60)
    print("SMA Crossover Strategy - Test")
    print("=" * 60)
    
    strategy = SmaCrossoverStrategy(fast_period=10, slow_period=50)
    print(f"  Strateji: {strategy}")
    print()
    
    for ticker in STOCKS:
        df = load_stock_data(ticker)
        df = strategy.run(df)
        
        buy_count = (df["Signal"] == 1).sum()
        sell_count = (df["Signal"] == -1).sum()
        name = get_short_name(ticker)
        
        print(f"  {name}: BUY={buy_count}, SELL={sell_count}")
    
    print("=" * 60)
