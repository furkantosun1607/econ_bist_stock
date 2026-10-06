"""
BIST Algorithmic Trading Challenge - Backtest Engine
=====================================================
Sinyalleri ve risk parametrelerini alarak gercekci portfoy simulasyonu yapar.

Temel Ozellikler:
- Nedensel next_open simulasyonu; same_close iyimser karsilastirma modu
- RiskManager entegrasyonu (stop-loss, trailing stop, ATR stop, max holding)
- Position sizing destegi (full capital, risk-bazli, yuzde-bazli)
- Komisyon ve slippage modellemesi
- Detayli trade log (giris/cikis tarihleri, fiyatlar, PnL, cikis sebebi)
- Gunluk mark-to-market equity curve
- Benchmark karsilastirmasi (PASS / FAIL analizi)
- Tek hisse veya tum 6 hisse icin toplu calistirma (run_stock, run_all)

Kullanim:
    from backtester import Backtester, Trade, BacktestResult
    from risk_manager import RiskManager
    from strategies.sma_crossover import SmaCrossoverStrategy

    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    bt = Backtester(initial_capital=100000, risk_manager=rm)

    # Tek hisse
    result = bt.run_stock("AKBNK.IS", strategy)
    result.print_summary()

    # Tum 6 hisse
    results = bt.run_all(strategy)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import (
    COMMISSION_RATE,
    INITIAL_CAPITAL,
    SLIPPAGE_RATE,
    STOCKS,
    TRADES_DIR,
    get_benchmark,
    get_short_name,
)
from risk_manager import RiskManager
from strategy_base import StrategyBase


# ============================================================
# Trade Veri Yapisi
# ============================================================

@dataclass
class Trade:
    """
    Tamamlanmis tek bir islemin (round-trip) tum detaylari.
    
    Attributes:
        entry_date: Pozisyona giris tarihi
        entry_price: Pozisyona giris fiyati (slippage dahil)
        exit_date: Pozisyondan cikis tarihi
        exit_price: Pozisyondan cikis fiyati (slippage dahil)
        shares: Islem goren hisse sayisi (lot/adet)
        pnl: Net kar/zarar (TL, komisyonlar dusulmus)
        pnl_pct: Net kar/zarar yuzdesi (% olarak, orn: 5.25 = %5.25)
        exit_reason: Cikis sebebi ("signal", "stop_loss", "trailing_stop", "atr_stop", "max_hold", "end_of_data")
        ticker: Hisse kodu (orn: "AKBNK.IS")
        bars_held: Pozisyonda gecen bar/gun sayisi
        commission: Bu islem icin odenen toplam komisyon (TL)
        cum_capital: Bu islem kapandiktan sonraki toplam sermaye (TL)
        entry_value: Giristeki toplam pozisyon degeri (TL)
        exit_value: Cikistaki toplam pozisyon degeri (TL)
    """
    entry_date: Any
    entry_price: float
    exit_date: Any
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str
    ticker: str = ""
    bars_held: int = 0
    commission: float = 0.0
    cum_capital: float = 0.0
    entry_value: float = 0.0
    exit_value: float = 0.0

    @property
    def is_winner(self) -> bool:
        """Islem karli mi?"""
        return self.pnl > 0

    @property
    def is_loser(self) -> bool:
        """Islem zararli mi?"""
        return self.pnl < 0

    @property
    def return_rate(self) -> float:
        """Ondalik formatta getiri (orn: 0.0525)."""
        return self.pnl_pct / 100.0

    def to_dict(self) -> dict[str, Any]:
        """Trade verisini sozluge cevirir."""
        entry_str = self.entry_date.strftime("%Y-%m-%d") if hasattr(self.entry_date, "strftime") else str(self.entry_date)
        exit_str = self.exit_date.strftime("%Y-%m-%d") if hasattr(self.exit_date, "strftime") else str(self.exit_date)
        return {
            "ticker": self.ticker,
            "entry_date": entry_str,
            "entry_price": round(self.entry_price, 4),
            "exit_date": exit_str,
            "exit_price": round(self.exit_price, 4),
            "shares": self.shares,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "exit_reason": self.exit_reason,
            "bars_held": self.bars_held,
            "commission": round(self.commission, 2),
            "cum_capital": round(self.cum_capital, 2),
        }

    def __repr__(self) -> str:
        entry_str = self.entry_date.strftime("%Y-%m-%d") if hasattr(self.entry_date, "strftime") else str(self.entry_date)
        exit_str = self.exit_date.strftime("%Y-%m-%d") if hasattr(self.exit_date, "strftime") else str(self.exit_date)
        sign = "+" if self.pnl >= 0 else ""
        return (
            f"Trade({self.ticker} | In: {entry_str} @ {self.entry_price:.2f} | "
            f"Out: {exit_str} @ {self.exit_price:.2f} | Qty: {self.shares} | "
            f"PnL: {sign}{self.pnl:,.2f} TL ({sign}{self.pnl_pct:.2f}%) | "
            f"Reason: {self.exit_reason})"
        )


# ============================================================
# Backtest Sonuc Yapisi
# ============================================================

@dataclass
class BacktestResult:
    """
    Backtest simulasyonu ciktisi ve performans ozeti.
    """
    ticker: str
    strategy_name: str
    initial_capital: float
    final_capital: float
    total_net_profit: float
    total_net_profit_pct: float
    trades: list[Trade]
    equity_curve: pd.Series
    df: pd.DataFrame
    commission_rate: float = 0.0
    slippage_rate: float = 0.0
    execution_mode: str = "next_open"

    @property
    def total_trades(self) -> int:
        """Toplam tamamlanan trade sayisi."""
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        """Karli trade sayisi."""
        return sum(1 for t in self.trades if t.is_winner)

    @property
    def losing_trades(self) -> int:
        """Zararli trade sayisi."""
        return sum(1 for t in self.trades if t.is_loser)

    @property
    def win_rate(self) -> float:
        """Kazanma orani (% olarak)."""
        return (self.winning_trades / self.total_trades * 100.0) if self.total_trades > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        """Gross Profit / Gross Loss."""
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if gross_loss > 0:
            return round(gross_profit / gross_loss, 2)
        return float("inf") if gross_profit > 0 else 0.0

    @property
    def max_drawdown(self) -> tuple[float, float]:
        """
        Maksimum drawdown miktar ve yuzdesi.
        Returns:
            (max_dd_tl: float, max_dd_pct: float)
        """
        if self.equity_curve.empty:
            return 0.0, 0.0
        peak = self.equity_curve.cummax()
        dd_tl = peak - self.equity_curve
        dd_pct = (dd_tl / peak) * 100.0
        return float(dd_tl.max()), float(dd_pct.max())

    @property
    def average_trade_pnl(self) -> float:
        """Islem basina ortalama net kar/zarar (TL)."""
        return (self.total_net_profit / self.total_trades) if self.total_trades > 0 else 0.0

    @property
    def average_trade_pct(self) -> float:
        """Islem basina ortalama getiri yuzdesi (%)."""
        if self.total_trades == 0:
            return 0.0
        return float(np.mean([t.pnl_pct for t in self.trades]))

    @property
    def largest_win(self) -> float:
        """En buyuk karli islem (TL)."""
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        return max(wins) if wins else 0.0

    @property
    def largest_loss(self) -> float:
        """En buyuk zararli islem (TL)."""
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        return min(losses) if losses else 0.0

    @property
    def average_bars_held(self) -> float:
        """Ortalama pozisyon tutma suresi (bar/gun)."""
        if self.total_trades == 0:
            return 0.0
        return float(np.mean([t.bars_held for t in self.trades]))

    @property
    def trades_df(self) -> pd.DataFrame:
        """Trade logunu pandas DataFrame olarak dondurur."""
        if not self.trades:
            return pd.DataFrame(columns=[
                "ticker", "entry_date", "entry_price", "exit_date", "exit_price",
                "shares", "pnl", "pnl_pct", "exit_reason", "bars_held",
                "commission", "cum_capital"
            ])
        return pd.DataFrame([t.to_dict() for t in self.trades])

    def compare_with_benchmark(self) -> dict[str, Any]:
        """
        Proje kuralina gore hissenin benchmark ile karsilastirmasi.
        
        Returns:
            dict: {
                "ticker": str,
                "passed": bool (final_capital > benchmark_final_capital),
                "meets_trade_rule": bool (total_trades >= 3),
                "fully_passed": bool (passed and meets_trade_rule),
                ...
            }
        """
        bm = get_benchmark(self.ticker)
        bm_final = bm.get("final_capital", 0.0)
        bm_profit = bm.get("net_profit", 0.0)

        diff_tl = self.final_capital - bm_final
        diff_pct = (diff_tl / bm_final * 100.0) if bm_final > 0 else 0.0
        passed = self.final_capital > bm_final
        meets_trade_rule = self.total_trades >= 3
        fully_passed = passed and meets_trade_rule

        return {
            "ticker": self.ticker,
            "short_name": get_short_name(self.ticker),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "net_profit": self.total_net_profit,
            "benchmark_final": bm_final,
            "benchmark_profit": bm_profit,
            "difference_tl": diff_tl,
            "difference_pct": diff_pct,
            "passed": passed,
            "total_trades": self.total_trades,
            "meets_trade_rule": meets_trade_rule,
            "fully_passed": fully_passed,
        }

    def save_trades(self, filepath: str | Path | None = None) -> Path:
        """Trade listesini CSV olarak kaydeder."""
        if filepath is None:
            short = get_short_name(self.ticker)
            filepath = TRADES_DIR / f"{short}_trades.csv"
        else:
            filepath = Path(filepath)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        self.trades_df.to_csv(filepath, index=False)
        return filepath

    def get_summary(self) -> dict[str, Any]:
        """Metrik ozet sozlügü."""
        max_dd_tl, max_dd_pct = self.max_drawdown
        bm_comp = self.compare_with_benchmark()
        return {
            "ticker": self.ticker,
            "strategy": self.strategy_name,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "net_profit": self.total_net_profit,
            "net_profit_pct": self.total_net_profit_pct,
            "benchmark_final": bm_comp["benchmark_final"],
            "benchmark_diff": bm_comp["difference_tl"],
            "passed": bm_comp["passed"],
            "fully_passed": bm_comp["fully_passed"],
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_tl": max_dd_tl,
            "max_drawdown_pct": max_dd_pct,
            "avg_trade_pnl": self.average_trade_pnl,
            "avg_trade_pct": self.average_trade_pct,
            "avg_bars_held": self.average_bars_held,
        }

    def print_summary(self):
        """Performans ozetini formatli konsola yazdirir."""
        short = get_short_name(self.ticker)
        bm_comp = self.compare_with_benchmark()
        max_dd_tl, max_dd_pct = self.max_drawdown

        status_str = "PASS" if bm_comp["passed"] else "FAIL"
        rule_str = "PASS" if bm_comp["meets_trade_rule"] else "FAIL (< 3 trade)"

        profit_sign = "+" if self.total_net_profit >= 0 else ""
        diff_sign = "+" if bm_comp["difference_tl"] >= 0 else ""

        print("=" * 65)
        print(f"BACKTEST SONUCU: {short} ({self.strategy_name})")
        print("=" * 65)
        print(f"  Baslangic Sermayesi : {self.initial_capital:>12,.2f} TL")
        print(f"  Bitis Sermayesi     : {self.final_capital:>12,.2f} TL")
        print(f"  Net Kar / Zarar     : {profit_sign}{self.total_net_profit:>11,.2f} TL ({profit_sign}{self.total_net_profit_pct:.2f}%)")
        print("-" * 65)
        print(f"  Benchmark Hedefi    : {bm_comp['benchmark_final']:>12,.2f} TL (+{bm_comp['benchmark_profit']:,.2f} TL)")
        print(f"  Benchmark Farki     : {diff_sign}{bm_comp['difference_tl']:>11,.2f} TL  [{status_str}]")
        print(f"  Minimum Trade Kurali: {self.total_trades} trade (Hedef >= 3)   [{rule_str}]")
        print("-" * 65)
        print(f"  Toplam Islem Sayisi : {self.total_trades:>5d}")
        print(f"  Kazanan / Kaybeden  : {self.winning_trades:>5d} / {self.losing_trades:<5d} (Kazanma: %{self.win_rate:.1f})")
        pf_str = f"{self.profit_factor:.2f}" if self.profit_factor != float("inf") else "inf"
        print(f"  Profit Factor       : {pf_str:>10s}")
        print(f"  Maksimum Drawdown   : -{max_dd_tl:>11,.2f} TL (-%{max_dd_pct:.2f})")
        print(f"  Ortalama Islem PnL  : {profit_sign}{self.average_trade_pnl:>11,.2f} TL ({profit_sign}{self.average_trade_pct:.2f}%)")
        print(f"  En Buyuk Kar        : +{self.largest_win:>11,.2f} TL")
        print(f"  En Buyuk Zarar      : {self.largest_loss:>12,.2f} TL")
        print(f"  Ortalama Sure       : {self.average_bars_held:>8.1f} gun/bar")
        print("=" * 65)


# ============================================================
# Backtest Motoru
# ============================================================

class Backtester:
    """
    Sinyal tabanli backtest motoru; nedensel emirler icin next_open kullanin.
    
    Parametreler:
        initial_capital: Baslangic sermayesi (TL, varsayilan: 100,000)
        risk_manager: RiskManager nesnesi (stop-loss, trailing stop, sizing vs.)
        commission_rate: Komisyon orani (orn: 0.001 = binde 1)
        slippage_rate: Slippage orani (orn: 0.0005)
        execution_mode: Emrin gerceklesme zamani
            "next_open"  : Sinyal gunu kapanista olusur, ertesi gun acilisinda islem yapilir (gercekci & onerilen)
            "same_close" : Kapanis bilgisiyle ayni kapanista dolum varsayan iyimser mod
        close_at_end: Backtest sonunda acik pozisyon varsa son gun kapanisinda zorla kapat
    """

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        risk_manager: RiskManager | None = None,
        commission_rate: float = COMMISSION_RATE,
        slippage_rate: float = SLIPPAGE_RATE,
        execution_mode: str = "next_open",
        close_at_end: bool = True,
    ):
        if execution_mode not in ("next_open", "same_close"):
            raise ValueError(f"Gecersiz execution_mode: '{execution_mode}'. 'next_open' veya 'same_close' secin.")

        self.initial_capital = float(initial_capital)
        self.risk_manager = risk_manager
        self.commission_rate = float(commission_rate)
        self.slippage_rate = float(slippage_rate)
        self.execution_mode = execution_mode
        self.close_at_end = close_at_end

    def _get_atr(self, row: Any) -> float | None:
        """Satirdan ATR degerini dinamik olarak ceker."""
        # Direkt ATR kolonlari
        for col in ["ATR", "ATR_14", "atr", "atr_14"]:
            if hasattr(row, col):
                val = getattr(row, col)
                if pd.notna(val) and np.isfinite(val) and val > 0:
                    return float(val)
        # hasattr bulunamadiysa sozluk/Series olarak bak
        if hasattr(row, "_asdict"):
            d = row._asdict()
            for k, v in d.items():
                if "ATR" in str(k).upper() and pd.notna(v) and np.isfinite(v) and v > 0:
                    return float(v)
        return None

    def _calc_shares(self, cash: float, fill_price: float, atr: float | None = None) -> int:
        """Mevcut nakit ve fiyata gore alinacak hisse adedini hesaplar."""
        if fill_price <= 0 or cash <= 0:
            return 0

        # Komisyon marjini birak
        effective_cash = cash / (1.0 + self.commission_rate)
        if effective_cash <= 0:
            return 0

        if self.risk_manager is not None:
            shares = self.risk_manager.calculate_position_size(effective_cash, fill_price, atr)
        else:
            shares = int(effective_cash / fill_price)

        # Komisyon dahil toplam maliyetin nakdi asmadigindan emin ol
        while shares > 0:
            total_needed = (shares * fill_price) * (1.0 + self.commission_rate)
            if total_needed <= cash + 1e-4:
                break
            shares -= 1

        return max(0, shares)

    def run(
        self,
        df: pd.DataFrame,
        ticker: str = "",
        strategy_name: str = "Strategy",
    ) -> BacktestResult:
        """
        Sinyal iceren DataFrame uzerinde backtest calistirir.
        
        Args:
            df: OHLCV + 'Signal' kolonu iceren DataFrame (index: DatetimeIndex)
            ticker: Hisse sembolu (orn: "AKBNK.IS")
            strategy_name: Strateji adi
        
        Returns:
            BacktestResult nesnesi
        """
        if "Signal" not in df.columns:
            raise ValueError("DataFrame 'Signal' kolonu icermelidir (-1, 0, 1).")

        required_cols = ["Open", "High", "Low", "Close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"DataFrame zorunlu '{col}' kolonunu icermelidir.")

        # Kopya al ve siralama dogrula
        df_work = df.copy()
        if not df_work.index.is_monotonic_increasing:
            df_work = df_work.sort_index()

        if self.execution_mode == "next_open":
            return self._run_next_open(df_work, ticker, strategy_name)
        else:
            return self._run_same_close(df_work, ticker, strategy_name)

    def _run_next_open(
        self,
        df: pd.DataFrame,
        ticker: str,
        strategy_name: str,
    ) -> BacktestResult:
        """
        Next Open Simulation:
        Gunun kapanisinda uretilen sinyal, ertesi gunun ACILISINDA gerceklesir.
        Sizing ve gun ici stoplar onceki tamamlanmis barin ATR degerini kullanir.
        Gun ici stoplar onceki tepeye gore sabittir; bugunun High degeri ancak
        sonraki barin stopunu etkiler. Gap durumunda dolum acilis fiyatindandir.
        """
        cash = self.initial_capital
        position: dict[str, Any] | None = None
        pending_order: dict[str, Any] | None = None
        trades: list[Trade] = []

        equity_list: list[float] = []
        position_list: list[int] = []
        action_list: list[str] = []
        pnl_record_list: list[float] = []

        n_bars = len(df)
        indices = df.index
        previous_atr = None

        for i, row in enumerate(df.itertuples()):
            dt = indices[i]
            open_p = float(row.Open)
            high_p = float(row.High)
            low_p = float(row.Low)
            close_p = float(row.Close)
            signal = int(row.Signal)
            atr = previous_atr
            previous_atr = self._get_atr(row)

            bar_action = ""
            bar_pnl = 0.0

            # ----------------------------------------------------
            # 1. ACILIS (Market Open): Bekleyen emirleri gerceklestir
            # ----------------------------------------------------
            if pending_order is not None:
                action = pending_order["action"]
                reason = pending_order["reason"]

                if action == "BUY" and position is None:
                    fill_price = open_p * (1.0 + self.slippage_rate)
                    shares = self._calc_shares(cash, fill_price, atr)
                    if shares > 0:
                        cost = shares * fill_price
                        comm = cost * self.commission_rate
                        cash -= (cost + comm)
                        position = {
                            "entry_date": dt,
                            "entry_price": fill_price,
                            "shares": shares,
                            "high": fill_price,
                            "low": fill_price,
                            "entry_bar": i,
                            "entry_cost": cost,
                            "entry_comm": comm,
                        }
                        bar_action = "BUY"
                    pending_order = None

                elif action == "SELL" and position is not None:
                    fill_price = open_p * (1.0 - self.slippage_rate)
                    gross = position["shares"] * fill_price
                    comm = gross * self.commission_rate
                    net_proceeds = gross - comm
                    cash += net_proceeds

                    total_comm = position["entry_comm"] + comm
                    trade_pnl = gross - position["entry_cost"] - total_comm
                    trade_cost_base = position["entry_cost"] + position["entry_comm"]
                    trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

                    trade = Trade(
                        ticker=ticker,
                        entry_date=position["entry_date"],
                        entry_price=position["entry_price"],
                        exit_date=dt,
                        exit_price=fill_price,
                        shares=position["shares"],
                        pnl=trade_pnl,
                        pnl_pct=trade_pct,
                        exit_reason=reason,
                        bars_held=i - position["entry_bar"],
                        commission=total_comm,
                        cum_capital=cash,
                        entry_value=position["entry_cost"],
                        exit_value=gross,
                    )
                    trades.append(trade)
                    bar_action = f"SELL ({reason})"
                    bar_pnl = trade_pnl
                    position = None
                    pending_order = None

            # ----------------------------------------------------
            # 2. GUN ICI (Intraday): RiskManager Stop Kontrolleri
            # ----------------------------------------------------
            if position is not None and self.risk_manager is not None:
                days_held = i - position["entry_bar"]

                # Stop seviyesini mevcut tepeye gore hesapla
                stop_price, stop_reason = self.risk_manager.get_stop_order(
                    entry_price=position["entry_price"],
                    high_since_entry=position["high"],
                    current_atr=atr,
                )

                if stop_price is not None and low_p <= stop_price:
                    # Stop tetiklendi!
                    # Gap down kontrolu: Acilis stopun altindaysa acilistan sat
                    raw_exit = min(open_p, stop_price)
                    fill_price = raw_exit * (1.0 - self.slippage_rate)

                    gross = position["shares"] * fill_price
                    comm = gross * self.commission_rate
                    net_proceeds = gross - comm
                    cash += net_proceeds

                    total_comm = position["entry_comm"] + comm
                    trade_pnl = gross - position["entry_cost"] - total_comm
                    trade_cost_base = position["entry_cost"] + position["entry_comm"]
                    trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

                    trade = Trade(
                        ticker=ticker,
                        entry_date=position["entry_date"],
                        entry_price=position["entry_price"],
                        exit_date=dt,
                        exit_price=fill_price,
                        shares=position["shares"],
                        pnl=trade_pnl,
                        pnl_pct=trade_pct,
                        exit_reason=stop_reason,
                        bars_held=days_held,
                        commission=total_comm,
                        cum_capital=cash,
                        entry_value=position["entry_cost"],
                        exit_value=gross,
                    )
                    trades.append(trade)
                    bar_action = f"SELL ({stop_reason})"
                    bar_pnl = trade_pnl
                    position = None
                else:
                    # Stop tetiklenmediyse gunun tepesini guncelle
                    position["high"] = max(position["high"], high_p)
                    position["low"] = min(position["low"], low_p)

            # ----------------------------------------------------
            # 3. KAPANIS (Market Close): Sinyal ve Max-Hold Kontrolu
            # ----------------------------------------------------
            if position is not None:
                days_held = i - position["entry_bar"]
                if (
                    self.risk_manager is not None
                    and self.risk_manager.max_holding_days is not None
                    and days_held >= self.risk_manager.max_holding_days
                ):
                    pending_order = {"action": "SELL", "reason": "max_hold"}
                elif signal == -1:
                    pending_order = {"action": "SELL", "reason": "signal"}
            else:
                # Pozisyon yoksa BUY sinyali kontrol et
                if signal == 1:
                    pending_order = {"action": "BUY", "reason": "signal"}

            # ----------------------------------------------------
            # 4. GUNLUK EQUITY (Mark-to-Market Kapanis)
            # ----------------------------------------------------
            if position is not None:
                day_equity = cash + position["shares"] * close_p
                pos_status = 1
            else:
                day_equity = cash
                pos_status = 0

            equity_list.append(day_equity)
            position_list.append(pos_status)
            action_list.append(bar_action)
            pnl_record_list.append(bar_pnl)

        # ----------------------------------------------------
        # 5. BITIS: Acik pozisyon kalmissa zorla kapat
        # ----------------------------------------------------
        if position is not None and self.close_at_end:
            last_dt = indices[-1]
            last_close = float(df.iloc[-1]["Close"])
            fill_price = last_close * (1.0 - self.slippage_rate)
            gross = position["shares"] * fill_price
            comm = gross * self.commission_rate
            net_proceeds = gross - comm
            cash += net_proceeds

            total_comm = position["entry_comm"] + comm
            trade_pnl = gross - position["entry_cost"] - total_comm
            trade_cost_base = position["entry_cost"] + position["entry_comm"]
            trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

            trade = Trade(
                ticker=ticker,
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                exit_date=last_dt,
                exit_price=fill_price,
                shares=position["shares"],
                pnl=trade_pnl,
                pnl_pct=trade_pct,
                exit_reason="end_of_data",
                bars_held=n_bars - 1 - position["entry_bar"],
                commission=total_comm,
                cum_capital=cash,
                entry_value=position["entry_cost"],
                exit_value=gross,
            )
            trades.append(trade)
            action_list[-1] = "SELL (end_of_data)"
            pnl_record_list[-1] = trade_pnl
            position_list[-1] = 0
            equity_list[-1] = cash
            position = None

        final_capital = cash if position is None else equity_list[-1]
        total_profit = final_capital - self.initial_capital
        total_profit_pct = (total_profit / self.initial_capital * 100.0) if self.initial_capital > 0 else 0.0

        equity_curve = pd.Series(equity_list, index=indices, name="Equity")
        df_result = df.copy()
        df_result["Equity"] = equity_curve
        df_result["Position"] = position_list
        df_result["Action"] = action_list
        df_result["Trade_PnL"] = pnl_record_list

        return BacktestResult(
            ticker=ticker,
            strategy_name=strategy_name,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            total_net_profit=round(total_profit, 2),
            total_net_profit_pct=round(total_profit_pct, 2),
            trades=trades,
            equity_curve=equity_curve,
            df=df_result,
            commission_rate=self.commission_rate,
            slippage_rate=self.slippage_rate,
            execution_mode="next_open",
        )

    def _run_same_close(
        self,
        df: pd.DataFrame,
        ticker: str,
        strategy_name: str,
    ) -> BacktestResult:
        """
        Same Close Simulation:
        Sinyal olustugu gunun KAPANISINDA islem yapildigi varsayilir (iyimser).
        Gun ici stoplar sadece onceki tamamlanmis ATR ve tepeyi kullanir.
        """
        cash = self.initial_capital
        position: dict[str, Any] | None = None
        trades: list[Trade] = []

        equity_list: list[float] = []
        position_list: list[int] = []
        action_list: list[str] = []
        pnl_record_list: list[float] = []

        n_bars = len(df)
        indices = df.index
        previous_atr = None

        for i, row in enumerate(df.itertuples()):
            dt = indices[i]
            open_p = float(row.Open)
            high_p = float(row.High)
            low_p = float(row.Low)
            close_p = float(row.Close)
            signal = int(row.Signal)
            intraday_atr = previous_atr
            atr = self._get_atr(row)
            previous_atr = atr

            bar_action = ""
            bar_pnl = 0.0

            # ----------------------------------------------------
            # 1. Pozisyon Varsa: Intraday Stop Kontrolleri
            # ----------------------------------------------------
            if position is not None and self.risk_manager is not None:
                days_held = i - position["entry_bar"]

                stop_price, stop_reason = self.risk_manager.get_stop_order(
                    entry_price=position["entry_price"],
                    high_since_entry=position["high"],
                    current_atr=intraday_atr,
                )

                if stop_price is not None and low_p <= stop_price:
                    raw_exit = min(open_p, stop_price)
                    fill_price = raw_exit * (1.0 - self.slippage_rate)

                    gross = position["shares"] * fill_price
                    comm = gross * self.commission_rate
                    cash += (gross - comm)

                    total_comm = position["entry_comm"] + comm
                    trade_pnl = gross - position["entry_cost"] - total_comm
                    trade_cost_base = position["entry_cost"] + position["entry_comm"]
                    trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

                    trade = Trade(
                        ticker=ticker,
                        entry_date=position["entry_date"],
                        entry_price=position["entry_price"],
                        exit_date=dt,
                        exit_price=fill_price,
                        shares=position["shares"],
                        pnl=trade_pnl,
                        pnl_pct=trade_pct,
                        exit_reason=stop_reason,
                        bars_held=days_held,
                        commission=total_comm,
                        cum_capital=cash,
                        entry_value=position["entry_cost"],
                        exit_value=gross,
                    )
                    trades.append(trade)
                    bar_action = f"SELL ({stop_reason})"
                    bar_pnl = trade_pnl
                    position = None
                else:
                    position["high"] = max(position["high"], high_p)
                    position["low"] = min(position["low"], low_p)

            # ----------------------------------------------------
            # 2. Pozisyon Varsa: Kapanis Cikis Kontrolleri (Max Hold veya SELL Sinyali)
            # ----------------------------------------------------
            if position is not None:
                days_held = i - position["entry_bar"]
                exit_reason = None

                if (
                    self.risk_manager is not None
                    and self.risk_manager.max_holding_days is not None
                    and days_held >= self.risk_manager.max_holding_days
                ):
                    exit_reason = "max_hold"
                elif signal == -1:
                    exit_reason = "signal"

                if exit_reason is not None:
                    fill_price = close_p * (1.0 - self.slippage_rate)
                    gross = position["shares"] * fill_price
                    comm = gross * self.commission_rate
                    cash += (gross - comm)

                    total_comm = position["entry_comm"] + comm
                    trade_pnl = gross - position["entry_cost"] - total_comm
                    trade_cost_base = position["entry_cost"] + position["entry_comm"]
                    trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

                    trade = Trade(
                        ticker=ticker,
                        entry_date=position["entry_date"],
                        entry_price=position["entry_price"],
                        exit_date=dt,
                        exit_price=fill_price,
                        shares=position["shares"],
                        pnl=trade_pnl,
                        pnl_pct=trade_pct,
                        exit_reason=exit_reason,
                        bars_held=days_held,
                        commission=total_comm,
                        cum_capital=cash,
                        entry_value=position["entry_cost"],
                        exit_value=gross,
                    )
                    trades.append(trade)
                    bar_action = f"SELL ({exit_reason})"
                    bar_pnl = trade_pnl
                    position = None

            # ----------------------------------------------------
            # 3. Pozisyon Yoksa: Kapanista BUY Sinyali
            # ----------------------------------------------------
            elif position is None and signal == 1:
                fill_price = close_p * (1.0 + self.slippage_rate)
                shares = self._calc_shares(cash, fill_price, atr)
                if shares > 0:
                    cost = shares * fill_price
                    comm = cost * self.commission_rate
                    cash -= (cost + comm)
                    position = {
                        "entry_date": dt,
                        "entry_price": fill_price,
                        "shares": shares,
                        "high": fill_price,
                        "low": fill_price,
                        "entry_bar": i,
                        "entry_cost": cost,
                        "entry_comm": comm,
                    }
                    bar_action = "BUY"

            # ----------------------------------------------------
            # 4. Kapanis Mark-to-Market Equity
            # ----------------------------------------------------
            if position is not None:
                day_equity = cash + position["shares"] * close_p
                pos_status = 1
            else:
                day_equity = cash
                pos_status = 0

            equity_list.append(day_equity)
            position_list.append(pos_status)
            action_list.append(bar_action)
            pnl_record_list.append(bar_pnl)

        # ----------------------------------------------------
        # 5. Bitis: Acik pozisyonu kapat
        # ----------------------------------------------------
        if position is not None and self.close_at_end:
            last_dt = indices[-1]
            last_close = float(df.iloc[-1]["Close"])
            fill_price = last_close * (1.0 - self.slippage_rate)
            gross = position["shares"] * fill_price
            comm = gross * self.commission_rate
            cash += (gross - comm)

            total_comm = position["entry_comm"] + comm
            trade_pnl = gross - position["entry_cost"] - total_comm
            trade_cost_base = position["entry_cost"] + position["entry_comm"]
            trade_pct = (trade_pnl / trade_cost_base * 100.0) if trade_cost_base > 0 else 0.0

            trade = Trade(
                ticker=ticker,
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                exit_date=last_dt,
                exit_price=fill_price,
                shares=position["shares"],
                pnl=trade_pnl,
                pnl_pct=trade_pct,
                exit_reason="end_of_data",
                bars_held=n_bars - 1 - position["entry_bar"],
                commission=total_comm,
                cum_capital=cash,
                entry_value=position["entry_cost"],
                exit_value=gross,
            )
            trades.append(trade)
            action_list[-1] = "SELL (end_of_data)"
            pnl_record_list[-1] = trade_pnl
            position_list[-1] = 0
            equity_list[-1] = cash
            position = None

        final_capital = cash if position is None else equity_list[-1]
        total_profit = final_capital - self.initial_capital
        total_profit_pct = (total_profit / self.initial_capital * 100.0) if self.initial_capital > 0 else 0.0

        equity_curve = pd.Series(equity_list, index=indices, name="Equity")
        df_result = df.copy()
        df_result["Equity"] = equity_curve
        df_result["Position"] = position_list
        df_result["Action"] = action_list
        df_result["Trade_PnL"] = pnl_record_list

        return BacktestResult(
            ticker=ticker,
            strategy_name=strategy_name,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            total_net_profit=round(total_profit, 2),
            total_net_profit_pct=round(total_profit_pct, 2),
            trades=trades,
            equity_curve=equity_curve,
            df=df_result,
            commission_rate=self.commission_rate,
            slippage_rate=self.slippage_rate,
            execution_mode="same_close",
        )

    # ========================================================
    # Yardimci Calistirma Metodlari
    # ========================================================

    def run_stock(
        self,
        ticker: str,
        strategy: StrategyBase,
        use_cache: bool = True,
    ) -> BacktestResult:
        """
        Tek bir hisse icin veriyi yukler, stratejiyi calistirir ve backtesti yurutur.
        """
        from data_loader import load_stock_data

        df = load_stock_data(ticker, use_cache=use_cache)
        df_signals = strategy.run(df)
        return self.run(df_signals, ticker=ticker, strategy_name=strategy.get_name())

    def run_all(
        self,
        strategy: StrategyBase,
        stocks: list[str] | None = None,
        use_cache: bool = True,
        print_table: bool = True,
    ) -> dict[str, BacktestResult]:
        """
        Tum hisseler icin backtest calistirir ve sonuclari dondurur.
        
        Args:
            strategy: Calistirilacak StrategyBase turetmesi
            stocks: Hisse listesi (varsayilan: config.STOCKS)
            use_cache: Veri cache'i kullanilsin mi
            print_table: Karsilastirma tablosu yazdirilsin mi
        
        Returns:
            dict[ticker, BacktestResult]
        """
        stocks = stocks or STOCKS
        results: dict[str, BacktestResult] = {}

        for ticker in stocks:
            res = self.run_stock(ticker, strategy, use_cache=use_cache)
            results[ticker] = res

        if print_table:
            self._print_comparison_table(results, strategy.get_name())

        return results

    @staticmethod
    def _print_comparison_table(results: dict[str, BacktestResult], strategy_name: str):
        """Tum hisselerin sonuclarini tek bir karsilastirmali tabloda gosterir."""
        print()
        print("=" * 105)
        print(f"BIST CHALLENGE - TOPLU STRATEJI SONUCLARI: {strategy_name}")
        print("=" * 105)
        headers = (
            f"{'Hisse':<8} | {'Baslangic':<11} | {'Final':<11} | "
            f"{'Net Kar':<12} | {'Benchmark':<11} | {'Fark':<11} | "
            f"{'Durum':<8} | {'Trades':<6} | {'Win%':<6} | {'MaxDD%':<7}"
        )
        print(headers)
        print("-" * 105)

        all_passed = True
        total_initial = 0.0
        total_final = 0.0

        for ticker, res in results.items():
            short = get_short_name(ticker)
            comp = res.compare_with_benchmark()
            _, max_dd_pct = res.max_drawdown

            status = "PASS" if comp["fully_passed"] else "FAIL"
            if not comp["fully_passed"]:
                all_passed = False

            total_initial += res.initial_capital
            total_final += res.final_capital

            diff_sign = "+" if comp["difference_tl"] >= 0 else ""
            profit_sign = "+" if res.total_net_profit >= 0 else ""

            row_str = (
                f"{short:<8} | "
                f"{res.initial_capital:>9,.0f}TL | "
                f"{res.final_capital:>9,.0f}TL | "
                f"{profit_sign}{res.total_net_profit:>10,.0f}TL | "
                f"{comp['benchmark_final']:>9,.0f}TL | "
                f"{diff_sign}{comp['difference_tl']:>9,.0f}TL | "
                f"{status:<8} | "
                f"{res.total_trades:>6d} | "
                f"{res.win_rate:>5.1f}% | "
                f"-{max_dd_pct:>5.1f}%"
            )
            print(row_str)

        print("-" * 105)
        total_profit = total_final - total_initial
        sign = "+" if total_profit >= 0 else ""
        print(
            f"{'TOPLAM':<8} | {total_initial:>9,.0f}TL | {total_final:>9,.0f}TL | "
            f"{sign}{total_profit:>10,.0f}TL |"
        )
        print("=" * 105)

        challenge_status = "TUM HISSELERDE BASARILI! (CHALLENGE PASSED) [OK]" if all_passed else "BAZI HISSELER ELENDI (CHALLENGE FAILED) [!]"
        print(f"Genel Challenge Durumu: {challenge_status}")
        print("=" * 105)
        print()


# ============================================================
# Modul Testi
# ============================================================

if __name__ == "__main__":
    from strategies.sma_crossover import SmaCrossoverStrategy

    print("=" * 65)
    print("BACKTESTER MODUL TESTI (Phase 5)")
    print("=" * 65)

    # 1. Test Stratejisi
    strategy = SmaCrossoverStrategy(fast_period=10, slow_period=50)

    # 2. Risk Yoneticisi olmadan test (Next Open)
    print("\n--- 1. Test: AKBNK (Risk Manager Yok, Next Open) ---")
    bt_no_rm = Backtester(initial_capital=100_000, risk_manager=None, execution_mode="next_open")
    res1 = bt_no_rm.run_stock("AKBNK.IS", strategy)
    res1.print_summary()

    # 3. Risk Yoneticisi ile test (Stop-Loss %5, Trailing Stop %3)
    print("\n--- 2. Test: AKBNK (Stop-Loss %5 + Trailing %3, Next Open) ---")
    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    bt_rm = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")
    res2 = bt_rm.run_stock("AKBNK.IS", strategy)
    res2.print_summary()

    # 4. Same Close Modu Testi
    print("\n--- 3. Test: AKBNK (Same Close Modu) ---")
    bt_sc = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="same_close")
    res3 = bt_sc.run_stock("AKBNK.IS", strategy)
    print(f"  Same Close Final Capital: {res3.final_capital:,.2f} TL | Trades: {res3.total_trades}")

    # 5. Tum 6 hisse uzerinde toplu calistirma testi
    print("\n--- 4. Test: Tum 6 Hisse Toplu Backtest (SMA Crossover) ---")
    results = bt_rm.run_all(strategy)

    # 6. Trade log CSV kaydetme testi
    csv_path = res2.save_trades()
    print(f"  Trade log basariyla kaydedildi: {csv_path.name}")
    print(f"  Ilk 2 islem detayi:")
    for t in res2.trades[:2]:
        print(f"    {t}")

    print("\n" + "=" * 65)
    print("Backtester testi basariyla tamamlandi! [OK]")
    print("=" * 65)
