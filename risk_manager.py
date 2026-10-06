"""
BIST Algorithmic Trading Challenge - Risk Manager
===================================================
Stratejiden bagimsiz risk yonetimi mekanizmalari.
Stop-loss, trailing stop, ATR stop, max holding period, position sizing.

Kullanim:
    from risk_manager import RiskManager

    rm = RiskManager(
        stop_loss_pct=0.05,
        trailing_stop_pct=0.03,
        max_holding_days=30,
    )

    # Cikis kontrolu
    should_exit, reason = rm.check_exit(
        entry_price=100, current_price=93,
        high_since_entry=110, current_atr=2.5, days_held=15
    )

    # Pozisyon buyuklugu
    shares = rm.calculate_position_size(capital=100000, price=50, atr=2.0)
"""

import numpy as np


class RiskManager:
    """
    Stratejiden bagimsiz risk yonetimi modulu.
    
    Birden fazla risk mekanizmasi ayni anda aktif olabilir.
    Herhangi biri tetiklenirse cikis sinyali verilir.
    
    Parametreler:
        stop_loss_pct: Sabit stop-loss yuzdesi (orn: 0.05 = %5)
        trailing_stop_pct: Trailing stop yuzdesi (orn: 0.03 = %3)
        atr_stop_multiplier: ATR bazli stop-loss carpani (orn: 2.0 = 2x ATR)
        max_holding_days: Maksimum pozisyon suresi (gun)
        position_size_pct: Sermayenin yuzde kaci kullanilacak (orn: 1.0 = %100)
        risk_per_trade_pct: Trade basina risk yuzdesi (position sizing icin)
    """
    
    def __init__(
        self,
        stop_loss_pct: float | None = None,
        trailing_stop_pct: float | None = None,
        atr_stop_multiplier: float | None = None,
        max_holding_days: int | None = None,
        position_size_pct: float = 1.0,
        risk_per_trade_pct: float | None = None,
    ):
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.atr_stop_multiplier = atr_stop_multiplier
        self.max_holding_days = max_holding_days
        self.position_size_pct = position_size_pct
        self.risk_per_trade_pct = risk_per_trade_pct
    
    def check_exit(
        self,
        entry_price: float,
        current_price: float,
        high_since_entry: float,
        current_atr: float | None = None,
        days_held: int = 0,
    ) -> tuple[bool, str]:
        """
        Pozisyondan cikis gerekip gerekmedegini kontrol eder.
        
        Birden fazla mekanizma aktifse, ilk tetiklenen kazanir.
        
        Args:
            entry_price: Giris fiyati
            current_price: Su anki fiyat
            high_since_entry: Giristen bu yana gorulmus en yuksek fiyat
            current_atr: Su anki ATR degeri (ATR stop icin gerekli)
            days_held: Pozisyonda gecen gun sayisi
        
        Returns:
            (should_exit: bool, reason: str)
            reason: "stop_loss", "trailing_stop", "atr_stop", "max_hold", "" (cikis yok)
        """
        # 1. Stop-Loss (sabit yuzde)
        if self.stop_loss_pct is not None:
            loss_pct = (entry_price - current_price) / entry_price
            if loss_pct >= self.stop_loss_pct:
                return True, "stop_loss"
        
        # 2. Trailing Stop (en yuksekten dusus)
        if self.trailing_stop_pct is not None:
            if high_since_entry > 0:
                drop_from_high = (high_since_entry - current_price) / high_since_entry
                if drop_from_high >= self.trailing_stop_pct:
                    return True, "trailing_stop"
        
        # 3. ATR Stop (ATR bazli stop-loss)
        if self.atr_stop_multiplier is not None and current_atr is not None:
            atr_stop_level = entry_price - (self.atr_stop_multiplier * current_atr)
            if current_price <= atr_stop_level:
                return True, "atr_stop"
        
        # 4. Maximum Holding Period
        if self.max_holding_days is not None:
            if days_held >= self.max_holding_days:
                return True, "max_hold"
        
        # Hicbir mekanizma tetiklenmedi
        return False, ""
    
    def calculate_position_size(
        self,
        capital: float,
        price: float,
        atr: float | None = None,
    ) -> int:
        """
        Kac adet hisse alinacagini hesaplar.
        
        Iki mod:
        1. position_size_pct modu: Sermayenin belirli yuzdesini kullan
        2. risk_per_trade_pct modu: Trade basina risk miktarina gore boyutla
           (ATR veya stop-loss bazli)
        
        Args:
            capital: Mevcut sermaye
            price: Hisse fiyati
            atr: Su anki ATR degeri (risk bazli sizing icin)
        
        Returns:
            int: Alinacak hisse sayisi (lot)
        """
        if price <= 0:
            return 0
        
        # Risk bazli position sizing
        if self.risk_per_trade_pct is not None and atr is not None and atr > 0:
            risk_amount = capital * self.risk_per_trade_pct
            # ATR stop kullaniliyorsa
            if self.atr_stop_multiplier is not None:
                risk_per_share = self.atr_stop_multiplier * atr
            # Stop-loss kullaniliyorsa
            elif self.stop_loss_pct is not None:
                risk_per_share = price * self.stop_loss_pct
            else:
                risk_per_share = atr  # Varsayilan: 1x ATR
            
            if risk_per_share > 0:
                shares = int(risk_amount / risk_per_share)
                # Sermayeyi asmamasi icin kontrol
                max_shares = int(capital / price)
                return min(shares, max_shares)
        
        # Yuzde bazli position sizing
        available = capital * self.position_size_pct
        shares = int(available / price)
        
        return max(shares, 0)
    
    def get_stop_price(
        self,
        entry_price: float,
        high_since_entry: float,
        current_atr: float | None = None,
    ) -> float | None:
        """
        Aktif stop fiyat seviyesini hesaplar (gorselleştirme icin).
        En siki (en yuksek) stop seviyesini dondurur.
        
        Returns:
            Stop fiyati veya None (stop aktif degilse)
        """
        stop_levels = []
        
        if self.stop_loss_pct is not None:
            stop_levels.append(entry_price * (1 - self.stop_loss_pct))
        
        if self.trailing_stop_pct is not None and high_since_entry > 0:
            stop_levels.append(high_since_entry * (1 - self.trailing_stop_pct))
        
        if self.atr_stop_multiplier is not None and current_atr is not None:
            stop_levels.append(entry_price - (self.atr_stop_multiplier * current_atr))
        
        if stop_levels:
            return max(stop_levels)  # En siki stop = en yuksek seviye
        return None
    
    def get_active_mechanisms(self) -> list[str]:
        """Aktif risk mekanizmalarini listeler."""
        active = []
        if self.stop_loss_pct is not None:
            active.append(f"Stop-Loss: {self.stop_loss_pct*100:.1f}%")
        if self.trailing_stop_pct is not None:
            active.append(f"Trailing Stop: {self.trailing_stop_pct*100:.1f}%")
        if self.atr_stop_multiplier is not None:
            active.append(f"ATR Stop: {self.atr_stop_multiplier}x ATR")
        if self.max_holding_days is not None:
            active.append(f"Max Hold: {self.max_holding_days} gun")
        if self.risk_per_trade_pct is not None:
            active.append(f"Risk/Trade: {self.risk_per_trade_pct*100:.1f}%")
        active.append(f"Position Size: {self.position_size_pct*100:.0f}%")
        return active
    
    def get_params(self) -> dict:
        """Aktif parametreleri dict olarak dondur."""
        return {
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "max_holding_days": self.max_holding_days,
            "position_size_pct": self.position_size_pct,
            "risk_per_trade_pct": self.risk_per_trade_pct,
        }
    
    def __repr__(self) -> str:
        mechanisms = ", ".join(self.get_active_mechanisms())
        return f"RiskManager({mechanisms})"


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Risk Manager - Test")
    print("=" * 60)
    
    # --- Test 1: Stop-Loss ---
    print("\n  --- Test 1: Stop-Loss ---")
    rm = RiskManager(stop_loss_pct=0.05)
    print(f"  {rm}")
    
    # Zarar %3 -> cikma
    exit, reason = rm.check_exit(entry_price=100, current_price=97,
                                  high_since_entry=102, days_held=5)
    print(f"  Fiyat 100->97 (%3 zarar): exit={exit}, reason='{reason}'")
    
    # Zarar %6 -> cik
    exit, reason = rm.check_exit(entry_price=100, current_price=94,
                                  high_since_entry=102, days_held=5)
    print(f"  Fiyat 100->94 (%6 zarar): exit={exit}, reason='{reason}'")
    
    # --- Test 2: Trailing Stop ---
    print("\n  --- Test 2: Trailing Stop ---")
    rm = RiskManager(trailing_stop_pct=0.03)
    print(f"  {rm}")
    
    # Zirve 110, su an 108 -> %1.8 dusus -> cikma
    exit, reason = rm.check_exit(entry_price=100, current_price=108,
                                  high_since_entry=110, days_held=10)
    print(f"  Zirve=110, Fiyat=108 (%1.8 dusus): exit={exit}, reason='{reason}'")
    
    # Zirve 110, su an 106 -> %3.6 dusus -> cik
    exit, reason = rm.check_exit(entry_price=100, current_price=106,
                                  high_since_entry=110, days_held=10)
    print(f"  Zirve=110, Fiyat=106 (%3.6 dusus): exit={exit}, reason='{reason}'")
    
    # --- Test 3: ATR Stop ---
    print("\n  --- Test 3: ATR Stop ---")
    rm = RiskManager(atr_stop_multiplier=2.0)
    print(f"  {rm}")
    
    # ATR=3, stop=100-6=94. Fiyat 95 -> cikma
    exit, reason = rm.check_exit(entry_price=100, current_price=95,
                                  high_since_entry=105, current_atr=3.0)
    print(f"  ATR=3, Stop=94, Fiyat=95: exit={exit}, reason='{reason}'")
    
    # Fiyat 93 -> cik
    exit, reason = rm.check_exit(entry_price=100, current_price=93,
                                  high_since_entry=105, current_atr=3.0)
    print(f"  ATR=3, Stop=94, Fiyat=93: exit={exit}, reason='{reason}'")
    
    # --- Test 4: Max Holding ---
    print("\n  --- Test 4: Max Holding Period ---")
    rm = RiskManager(max_holding_days=20)
    print(f"  {rm}")
    
    exit, reason = rm.check_exit(entry_price=100, current_price=105,
                                  high_since_entry=105, days_held=15)
    print(f"  15 gun: exit={exit}, reason='{reason}'")
    
    exit, reason = rm.check_exit(entry_price=100, current_price=105,
                                  high_since_entry=105, days_held=20)
    print(f"  20 gun: exit={exit}, reason='{reason}'")
    
    # --- Test 5: Position Sizing ---
    print("\n  --- Test 5: Position Sizing ---")
    rm = RiskManager(position_size_pct=1.0)
    shares = rm.calculate_position_size(capital=100_000, price=50)
    print(f"  %100 sermaye, fiyat=50: {shares} lot")
    
    rm = RiskManager(position_size_pct=0.5)
    shares = rm.calculate_position_size(capital=100_000, price=50)
    print(f"  %50 sermaye, fiyat=50: {shares} lot")
    
    # Risk bazli
    rm = RiskManager(risk_per_trade_pct=0.02, atr_stop_multiplier=2.0)
    shares = rm.calculate_position_size(capital=100_000, price=50, atr=3.0)
    print(f"  Risk %2, ATR=3, 2x stop, fiyat=50: {shares} lot")
    
    # --- Test 6: Kombinasyon ---
    print("\n  --- Test 6: Coklu Mekanizma ---")
    rm = RiskManager(
        stop_loss_pct=0.07,
        trailing_stop_pct=0.04,
        atr_stop_multiplier=2.5,
        max_holding_days=30,
        position_size_pct=1.0,
    )
    print(f"  {rm}")
    
    stop = rm.get_stop_price(entry_price=100, high_since_entry=110, current_atr=3.0)
    print(f"  Aktif stop seviyesi: {stop:.2f} TL")
    
    print("\n" + "=" * 60)
