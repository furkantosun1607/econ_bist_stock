"""
BIST Algorithmic Trading Challenge - Strategy Base Class
=========================================================
Tum stratejilerin uyması gereken interface/abstract class.
Yeni strateji eklemek icin:
    1. StrategyBase'den turet
    2. generate_signals() metodunu yaz
    3. runner.py'da stratejini sec

Kullanim:
    from strategy_base import StrategyBase

    class MyStrategy(StrategyBase):
        def generate_signals(self, df):
            # ... sinyal uret ...
            return df
"""

from abc import ABC, abstractmethod
import pandas as pd


class StrategyBase(ABC):
    """
    Tum trading stratejileri icin temel sinif (Abstract Base Class).
    
    Her strateji su kurallara uymalidir:
    - generate_signals() metodu DataFrame'e 'Signal' kolonu eklemeli
    - Signal degerleri: 1 (BUY), -1 (SELL), 0 (HOLD)
    - Gelecek verisi kullanilamaz (No Look-Ahead)
    - En az 3 tamamlanmis trade uretmeli (her hisse icin)
    """
    
    def __init__(self, name: str = "BaseStrategy", params: dict | None = None):
        """
        Args:
            name: Strateji adi (raporlama icin)
            params: Strateji parametreleri dict'i
        """
        self._name = name
        self._params = params or {}
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ana sinyal uretim metodu. Her strateji bunu implement etmeli.
        
        Args:
            df: OHLCV verisi iceren DataFrame (indikatorler eklenebilir)
        
        Returns:
            pd.DataFrame: 'Signal' kolonu eklenmis DataFrame
                Signal = 1  -> BUY (pozisyon ac)
                Signal = -1 -> SELL (pozisyon kapat)
                Signal = 0  -> HOLD (bir sey yapma)
        
        KURALLAR:
        - Sadece o ana kadar olan veriyi kullan (no look-ahead)
        - df'yi modify ederek dondur (in-place veya copy)
        - 'Signal' kolonu int olmali
        """
        pass
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Veriyi stratejiye hazirla (indikatorleri ekle).
        Alt siniflar override edebilir.
        Varsayilan: hicbir sey yapmaz, ham veriyi dondurur.
        
        Args:
            df: Ham OHLCV DataFrame
        
        Returns:
            Indikatorler eklenmis DataFrame
        """
        return df.copy()
    
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Stratejiyi calistir: veri hazirla + sinyal uret.
        Bu metod genellikle override edilmez.
        
        Args:
            df: Ham OHLCV DataFrame
        
        Returns:
            Sinyaller eklenmis DataFrame
        """
        # 1. Veriyi hazirla (indikatorleri ekle)
        df_prepared = self.prepare_data(df)
        
        # 2. Sinyalleri uret
        df_signals = self.generate_signals(df_prepared)
        
        # 3. Dogrulama
        self._validate_signals(df_signals)
        
        return df_signals
    
    def _validate_signals(self, df: pd.DataFrame):
        """Sinyal kolonunun varligini ve formatini kontrol et."""
        if "Signal" not in df.columns:
            raise ValueError(
                f"[{self._name}] generate_signals() 'Signal' kolonu eklemedi!"
            )
        
        valid_values = {-1, 0, 1}
        unique_signals = set(df["Signal"].dropna().unique())
        invalid = unique_signals - valid_values
        if invalid:
            raise ValueError(
                f"[{self._name}] Gecersiz sinyal degerleri: {invalid}. "
                f"Beklenen: {valid_values}"
            )
        
        buy_count = (df["Signal"] == 1).sum()
        sell_count = (df["Signal"] == -1).sum()
        
        if buy_count == 0:
            print(f"  [WARN] {self._name}: Hic BUY sinyali uretilmedi!")
        if sell_count == 0:
            print(f"  [WARN] {self._name}: Hic SELL sinyali uretilmedi!")
    
    def get_name(self) -> str:
        """Strateji adini dondur."""
        return self._name
    
    def get_params(self) -> dict:
        """Aktif parametreleri dondur."""
        return self._params.copy()
    
    def set_params(self, **kwargs):
        """Parametreleri guncelle."""
        self._params.update(kwargs)
    
    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v}" for k, v in self._params.items())
        return f"{self._name}({params_str})"
