"""
BIST Algorithmic Trading Challenge - Performance Metrics Module
================================================================
Performans metriklerinin hesaplanmasi, risk analizi ve benchmark karsilastirmasi.

Zorunlu Metrikler (Proje Sartnamesi):
- Net Profit (TL ve %)
- Final Capital (TL)
- Total Trades (Toplam islem sayisi, hedef >= 3)
- Winning Trades (Kazanan islem sayisi)
- Losing Trades (Kaybeden islem sayisi)
- Win Rate (% kazanma orani)
- Maximum Drawdown (TL ve % maksimum sermaye kaybi)
- Profit Factor (Brut kar / brut zarar)
- Average Trade (Ortalama islem basina kar/zarar)

Ekstra Risk ve Getiri Metrikleri:
- Sharpe Ratio (Yilliklandirilmis)
- Sortino Ratio (Asagi yonlu volatiliteye gore risk-ayarlanmis getiri)
- Calmar Ratio (CAGR / Max Drawdown)
- Payoff Ratio (Ortalama kazanc / ortalama kayip)
- Max Drawdown Duration (En uzun kayip periyodu)
- Max Consecutive Wins / Losses (Ardisik kazanc/kayip serisi)
- Exit Reason Breakdown (Cikis sebeplerinin dagilimi)

Kullanim:
    from metrics import (
        calculate_metrics,
        compare_with_benchmark,
        generate_summary_table,
        evaluate_challenge,
    )

    # Tek backtest sonucu icin
    metrics = calculate_metrics(result)
    print(metrics)

    # Benchmark karsilastirmasi
    comp = compare_with_benchmark(result.final_capital, "AKBNK.IS", total_trades=result.total_trades)

    # Toplu 6 hisse ozet tablosu
    df_summary = generate_summary_table(results)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from config import (
    BENCHMARKS,
    INITIAL_CAPITAL,
    RESULTS_DIR,
    STOCKS,
    get_benchmark,
    get_short_name,
)

if TYPE_CHECKING:
    from backtester import BacktestResult, Trade


# ============================================================
# Performans Metrikleri Veri Yapisi
# ============================================================

@dataclass
class PerformanceMetrics:
    """Tek bir hissenin tum performans ve risk metrikleri."""
    ticker: str
    short_name: str
    strategy_name: str
    initial_capital: float
    final_capital: float
    net_profit: float
    net_profit_pct: float
    cagr: float
    
    # Islem Metrikleri
    total_trades: int
    winning_trades: int
    losing_trades: int
    break_even_trades: int
    win_rate: float
    profit_factor: float
    
    # Risk ve Drawdown Metrikleri
    max_drawdown_tl: float
    max_drawdown_pct: float
    max_drawdown_duration_bars: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Islem Istatistikleri
    avg_trade_pnl: float
    avg_trade_pct: float
    avg_win_pnl: float
    avg_loss_pnl: float
    payoff_ratio: float
    largest_win_pnl: float
    largest_loss_pnl: float
    avg_bars_held: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    # Benchmark Bilgisi
    benchmark_final: float
    benchmark_profit: float
    benchmark_diff_tl: float
    benchmark_passed: bool
    meets_trade_rule: bool
    challenge_passed: bool
    
    # Cikis Dagilimi
    exit_reasons: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Metrikleri duz sozluge cevirir."""
        return asdict(self)


# ============================================================
# Benchmark Karsilastirma Fonksiyonlari
# ============================================================

def compare_with_benchmark(
    final_capital: float,
    stock: str,
    total_trades: int = 0,
) -> dict[str, Any]:
    """
    Tek bir hisse icin final sermayeyi benchmark hedefiyle karsilastirir.
    
    Args:
        final_capital: Strateji sonucundaki bitis sermayesi
        stock: Hisse sembolu ("AKBNK.IS" veya "AKBNK")
        total_trades: Tamamlanan islem sayisi (>= 3 kurali kontrolu icin)
        
    Returns:
        dict: Benchmark karsilastirma detaylari
    """
    # Hisse sembolunu normalize et
    ticker = stock if stock.endswith(".IS") else f"{stock}.IS"
    short_name = get_short_name(ticker)

    bm = get_benchmark(ticker)
    bm_final = float(bm.get("final_capital", 0.0))
    bm_profit = float(bm.get("net_profit", 0.0))

    diff_tl = final_capital - bm_final
    diff_pct = (diff_tl / bm_final * 100.0) if bm_final > 0 else 0.0
    
    passed_capital = final_capital > bm_final
    meets_trade_rule = (total_trades >= 3) if total_trades > 0 else True
    fully_passed = passed_capital and meets_trade_rule

    return {
        "ticker": ticker,
        "short_name": short_name,
        "strategy_final": round(final_capital, 2),
        "benchmark_final": round(bm_final, 2),
        "benchmark_profit": round(bm_profit, 2),
        "difference_tl": round(diff_tl, 2),
        "difference_pct": round(diff_pct, 2),
        "passed": passed_capital,
        "total_trades": total_trades,
        "meets_trade_rule": meets_trade_rule,
        "fully_passed": fully_passed,
        "status": "PASS" if fully_passed else "FAIL",
    }


# ============================================================
# Istatistiksel Hesaplama Yardimcilari
# ============================================================

def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, float, int]:
    """
    Equity curve uzerinden maksimum drawdown miktarini, yuzdesini ve suresini hesaplar.
    
    Returns:
        (max_dd_amount, max_dd_pct, max_duration_bars)
    """
    if equity_curve.empty:
        return 0.0, 0.0, 0

    peak = equity_curve.cummax()
    dd_amount = peak - equity_curve
    dd_pct = (dd_amount / peak) * 100.0

    max_dd_amount = float(dd_amount.max())
    max_dd_pct = float(dd_pct.max())

    # Drawdown suresi (en uzun toparlanamama bar sayisi)
    is_underwater = dd_amount > 0
    duration_bars = 0
    max_duration = 0
    for underwater in is_underwater:
        if underwater:
            duration_bars += 1
            if duration_bars > max_duration:
                max_duration = duration_bars
        else:
            duration_bars = 0

    return round(max_dd_amount, 2), round(max_dd_pct, 2), max_duration


def calculate_sharpe_ratio(
    equity_curve: pd.Series,
    risk_free_rate: float = 0.0,
    annual_factor: int = 252,
) -> float:
    """Yilliklandirilmis Sharpe Oranini hesaplar."""
    if len(equity_curve) < 2:
        return 0.0

    returns = equity_curve.pct_change().dropna()
    std = returns.std()
    if std == 0 or np.isnan(std):
        return 0.0

    rf_daily = (1.0 + risk_free_rate) ** (1.0 / annual_factor) - 1.0
    excess_returns = returns - rf_daily
    mean_excess = excess_returns.mean()

    sharpe = (mean_excess / std) * np.sqrt(annual_factor)
    return round(float(sharpe), 2)


def calculate_sortino_ratio(
    equity_curve: pd.Series,
    risk_free_rate: float = 0.0,
    annual_factor: int = 252,
) -> float:
    """Yilliklandirilmis Sortino Oranini (sadece negatif volatilite) hesaplar."""
    if len(equity_curve) < 2:
        return 0.0

    returns = equity_curve.pct_change().dropna()
    rf_daily = (1.0 + risk_free_rate) ** (1.0 / annual_factor) - 1.0
    excess_returns = returns - rf_daily

    # Standart Downside Deviation (Semi-variance)
    downside_diff = np.minimum(0.0, excess_returns)
    downside_variance = np.mean(downside_diff ** 2)

    if downside_variance <= 0:
        return float("inf") if excess_returns.mean() > 0 else 0.0

    downside_dev = np.sqrt(downside_variance)
    sortino = (excess_returns.mean() / downside_dev) * np.sqrt(annual_factor)
    return round(float(sortino), 2)


def calculate_cagr(
    initial_capital: float,
    final_capital: float,
    n_bars: int,
    annual_factor: int = 252,
) -> float:
    """Bilesik Yillik Buyume Oranini (CAGR %) hesaplar."""
    if initial_capital <= 0 or final_capital <= 0 or n_bars <= 0:
        return 0.0
    years = n_bars / annual_factor
    if years <= 0:
        return 0.0
    cagr = ((final_capital / initial_capital) ** (1.0 / years) - 1.0) * 100.0
    return round(float(cagr), 2)


def calculate_streaks(trades: list[Any]) -> tuple[int, int]:
    """Ardisik maksimum kazanc ve kayip serilerini hesaplar."""
    max_wins = 0
    max_losses = 0
    cur_wins = 0
    cur_losses = 0

    for t in trades:
        pnl = getattr(t, "pnl", 0.0)
        if pnl > 0:
            cur_wins += 1
            cur_losses = 0
            if cur_wins > max_wins:
                max_wins = cur_wins
        elif pnl < 0:
            cur_losses += 1
            cur_wins = 0
            if cur_losses > max_losses:
                max_losses = cur_losses
        else:
            cur_wins = 0
            cur_losses = 0

    return max_wins, max_losses


# ============================================================
# Ana Metrik Hesaplama Fonksiyonu
# ============================================================

def calculate_metrics(result: Any) -> PerformanceMetrics:
    """
    BacktestResult nesnesinden (veya uyumlu veri yapisindan) eksiksiz performans metriklerini hesaplar.
    
    Args:
        result: backtester.BacktestResult nesnesi
        
    Returns:
        PerformanceMetrics nesnesi
    """
    ticker = getattr(result, "ticker", "")
    short_name = get_short_name(ticker)
    strategy_name = getattr(result, "strategy_name", "Strategy")
    initial_cap = float(getattr(result, "initial_capital", INITIAL_CAPITAL))
    final_cap = float(getattr(result, "final_capital", initial_cap))
    trades = getattr(result, "trades", [])
    equity_curve = getattr(result, "equity_curve", pd.Series([initial_cap]))

    # Kar / Zarar
    net_profit = final_cap - initial_cap
    net_profit_pct = (net_profit / initial_cap * 100.0) if initial_cap > 0 else 0.0
    n_bars = len(equity_curve)
    cagr = calculate_cagr(initial_cap, final_cap, n_bars)

    # Islem Sayilari
    total_trades = len(trades)
    win_trades = [t for t in trades if getattr(t, "pnl", 0) > 0]
    loss_trades = [t for t in trades if getattr(t, "pnl", 0) < 0]
    be_trades = [t for t in trades if getattr(t, "pnl", 0) == 0]

    n_wins = len(win_trades)
    n_losses = len(loss_trades)
    n_be = len(be_trades)

    win_rate = (n_wins / total_trades * 100.0) if total_trades > 0 else 0.0

    # Profit Factor
    gross_profit = sum(t.pnl for t in win_trades)
    gross_loss = abs(sum(t.pnl for t in loss_trades))
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    # Drawdown & Oranlar
    max_dd_tl, max_dd_pct, max_dd_dur = calculate_max_drawdown(equity_curve)
    sharpe = calculate_sharpe_ratio(equity_curve)
    sortino = calculate_sortino_ratio(equity_curve)
    calmar = round(cagr / max_dd_pct, 2) if max_dd_pct > 0 else 0.0

    # Ortalama Islem Detaylari
    avg_trade_pnl = (net_profit / total_trades) if total_trades > 0 else 0.0
    avg_trade_pct = float(np.mean([t.pnl_pct for t in trades])) if total_trades > 0 else 0.0
    avg_win_pnl = float(np.mean([t.pnl for t in win_trades])) if n_wins > 0 else 0.0
    avg_loss_pnl = float(np.mean([t.pnl for t in loss_trades])) if n_losses > 0 else 0.0
    payoff = (avg_win_pnl / abs(avg_loss_pnl)) if abs(avg_loss_pnl) > 0 else 0.0

    largest_win = max([t.pnl for t in win_trades]) if n_wins > 0 else 0.0
    largest_loss = min([t.pnl for t in loss_trades]) if n_losses > 0 else 0.0
    avg_bars_held = float(np.mean([getattr(t, "bars_held", 0) for t in trades])) if total_trades > 0 else 0.0
    max_wins_streak, max_loss_streak = calculate_streaks(trades)

    # Cikis sebepleri dagilimi
    exit_reasons: dict[str, int] = {}
    for t in trades:
        reason = getattr(t, "exit_reason", "unknown")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    # Benchmark Kontrolu
    bm_comp = compare_with_benchmark(final_cap, ticker, total_trades=total_trades)

    return PerformanceMetrics(
        ticker=ticker,
        short_name=short_name,
        strategy_name=strategy_name,
        initial_capital=initial_cap,
        final_capital=round(final_cap, 2),
        net_profit=round(net_profit, 2),
        net_profit_pct=round(net_profit_pct, 2),
        cagr=cagr,
        total_trades=total_trades,
        winning_trades=n_wins,
        losing_trades=n_losses,
        break_even_trades=n_be,
        win_rate=round(win_rate, 2),
        profit_factor=profit_factor,
        max_drawdown_tl=max_dd_tl,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_duration_bars=max_dd_dur,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        avg_trade_pnl=round(avg_trade_pnl, 2),
        avg_trade_pct=round(avg_trade_pct, 2),
        avg_win_pnl=round(avg_win_pnl, 2),
        avg_loss_pnl=round(avg_loss_pnl, 2),
        payoff_ratio=round(payoff, 2),
        largest_win_pnl=round(largest_win, 2),
        largest_loss_pnl=round(largest_loss, 2),
        avg_bars_held=round(avg_bars_held, 1),
        max_consecutive_wins=max_wins_streak,
        max_consecutive_losses=max_loss_streak,
        benchmark_final=bm_comp["benchmark_final"],
        benchmark_profit=bm_comp["benchmark_profit"],
        benchmark_diff_tl=bm_comp["difference_tl"],
        benchmark_passed=bm_comp["passed"],
        meets_trade_rule=bm_comp["meets_trade_rule"],
        challenge_passed=bm_comp["fully_passed"],
        exit_reasons=exit_reasons,
    )


# ============================================================
# Raporlama ve Tablo Uretimi
# ============================================================

def generate_summary_table(
    results: dict[str, Any],
) -> pd.DataFrame:
    """
    Tum hisselerin backtest sonuclarindan karsilastirmali ozet DataFrame uretir.
    
    Args:
        results: dict[ticker, BacktestResult]
        
    Returns:
        pd.DataFrame: Metrikler ozet tablosu
    """
    rows = []
    for ticker, res in results.items():
        m = calculate_metrics(res)
        status_str = "PASS" if m.challenge_passed else "FAIL"

        rows.append({
            "Hisse": m.short_name,
            "Baslangic (TL)": m.initial_capital,
            "Final (TL)": m.final_capital,
            "Net Kar (TL)": m.net_profit,
            "Net Kar (%)": m.net_profit_pct,
            "Benchmark (TL)": m.benchmark_final,
            "Fark (TL)": m.benchmark_diff_tl,
            "Durum": status_str,
            "Trades": m.total_trades,
            "Win Rate (%)": m.win_rate,
            "Profit Factor": m.profit_factor if m.profit_factor != float("inf") else 999.0,
            "Max DD (%)": m.max_drawdown_pct,
            "Sharpe": m.sharpe_ratio,
            "Avg Trade (TL)": m.avg_trade_pnl,
        })

    df = pd.DataFrame(rows)
    return df


def evaluate_challenge(results: dict[str, Any]) -> dict[str, Any]:
    """
    Tum portfoy icin BIST Challenge kural degerlendirmesini yapar.
    
    Kural: Her 6 hisse de bireysel olarak benchmark'i gecmeli VE en az 3 trade yapmali.
    
    Returns:
        dict: Challenge genel durum ozeti
    """
    total_stocks = len(results)
    passed_stocks: list[str] = []
    failed_stocks: list[str] = []

    total_initial = 0.0
    total_final = 0.0
    total_trades = 0

    stock_details = {}

    for ticker, res in results.items():
        m = calculate_metrics(res)
        total_initial += m.initial_capital
        total_final += m.final_capital
        total_trades += m.total_trades

        detail = {
            "short_name": m.short_name,
            "final_capital": m.final_capital,
            "benchmark_final": m.benchmark_final,
            "diff_tl": m.benchmark_diff_tl,
            "passed_benchmark": m.benchmark_passed,
            "total_trades": m.total_trades,
            "meets_trade_rule": m.meets_trade_rule,
            "fully_passed": m.challenge_passed,
        }
        stock_details[m.short_name] = detail

        if m.challenge_passed:
            passed_stocks.append(m.short_name)
        else:
            failed_stocks.append(m.short_name)

    all_passed = (len(passed_stocks) == total_stocks) and (total_stocks >= 6)
    total_profit = total_final - total_initial
    total_profit_pct = (total_profit / total_initial * 100.0) if total_initial > 0 else 0.0

    return {
        "all_passed": all_passed,
        "challenge_status": "CHALLENGE PASSED" if all_passed else "CHALLENGE FAILED",
        "passed_stocks": passed_stocks,
        "failed_stocks": failed_stocks,
        "passed_count": len(passed_stocks),
        "total_count": total_stocks,
        "total_initial_capital": round(total_initial, 2),
        "total_final_capital": round(total_final, 2),
        "total_net_profit": round(total_profit, 2),
        "total_net_profit_pct": round(total_profit_pct, 2),
        "total_trades": total_trades,
        "stock_details": stock_details,
    }


def save_metrics_to_csv(
    df_metrics: pd.DataFrame,
    filepath: str | Path | None = None,
) -> Path:
    """Ozet metrik tablosunu CSV olarak kaydeder."""
    if filepath is None:
        filepath = RESULTS_DIR / "metrics_summary.csv"
    else:
        filepath = Path(filepath)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    df_metrics.to_csv(filepath, index=False)
    return filepath


def generate_markdown_report(results: dict[str, Any], strategy_name: str = "Strategy") -> str:
    """GitHub / Assignment icin tam markdown performans raporu olusturur."""
    eval_res = evaluate_challenge(results)
    df = generate_summary_table(results)

    status_badge = "🏆 **PASSED**" if eval_res["all_passed"] else "⚠️ **FAILED**"

    lines = [
        f"# BIST Algorithmic Trading Challenge - Performans Raporu",
        f"**Strateji:** {strategy_name}  ",
        f"**Genel Durum:** {status_badge} ({eval_res['passed_count']}/{eval_res['total_count']} hisse basarili)  ",
        f"**Toplam Portfoy:** {eval_res['total_initial_capital']:,.0f} TL -> {eval_res['total_final_capital']:,.0f} TL "
        f"({eval_res['total_net_profit']:+,.0f} TL | {eval_res['total_net_profit_pct']:+.2f}%)  ",
        "",
        "## Hisse Bazli Benchmark Karsilastirmasi",
        "",
        "| Hisse | Baslangic | Final | Net Kar | Benchmark | Fark | Trades | Win% | MaxDD% | Durum |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for _, row in df.iterrows():
        status_icon = "PASS" if row["Durum"] == "PASS" else "FAIL"
        profit_sign = "+" if row["Net Kar (TL)"] >= 0 else ""
        diff_sign = "+" if row["Fark (TL)"] >= 0 else ""
        lines.append(
            f"| **{row['Hisse']}** | {row['Baslangic (TL)']:,.0f} TL | {row['Final (TL)']:,.0f} TL | "
            f"{profit_sign}{row['Net Kar (TL)']:,.0f} TL | {row['Benchmark (TL)']:,.0f} TL | "
            f"{diff_sign}{row['Fark (TL)']:,.0f} TL | {row['Trades']} | "
            f"%{row['Win Rate (%)']:.1f} | -%{row['Max DD (%)']:.1f} | {status_icon} |"
        )

    lines.extend([
        "",
        "## Challenge Kurali Hatirlatmasi",
        "> [!IMPORTANT]",
        "> Toplam portfoy kari tek basina yeterli degildir. 6 hissenin tamaminin bireysel benchmark hedefini gecmesi ve her birinde en az 3 tamamlanmis islem bulunmasi zorunludur.",
        "",
    ])

    return "\n".join(lines)


def print_metrics_summary(results: dict[str, Any], strategy_name: str = "Strategy"):
    """Tum sonuclari konsola formatli yazdirir."""
    eval_res = evaluate_challenge(results)
    df = generate_summary_table(results)

    print()
    print("=" * 110)
    print(f"BIST CHALLENGE - PERFORMANS METRIKLERI VE BENCHMARK ANALIZI: {strategy_name}")
    print("=" * 110)
    headers = (
        f"{'Hisse':<8} | {'Baslangic':<11} | {'Final':<11} | "
        f"{'Net Kar':<12} | {'Benchmark':<11} | {'Fark':<11} | "
        f"{'Trades':<6} | {'Win%':<6} | {'PF':<6} | {'MaxDD%':<7} | {'Durum':<6}"
    )
    print(headers)
    print("-" * 110)

    for _, row in df.iterrows():
        profit_sign = "+" if row["Net Kar (TL)"] >= 0 else ""
        diff_sign = "+" if row["Fark (TL)"] >= 0 else ""
        pf_str = f"{row['Profit Factor']:.2f}" if row['Profit Factor'] != 999.0 else "inf"

        line = (
            f"{row['Hisse']:<8} | "
            f"{row['Baslangic (TL)']:>9,.0f}TL | "
            f"{row['Final (TL)']:>9,.0f}TL | "
            f"{profit_sign}{row['Net Kar (TL)']:>10,.0f}TL | "
            f"{row['Benchmark (TL)']:>9,.0f}TL | "
            f"{diff_sign}{row['Fark (TL)']:>9,.0f}TL | "
            f"{int(row['Trades']):>6d} | "
            f"{row['Win Rate (%)']:>5.1f}% | "
            f"{pf_str:>6s} | "
            f"-{row['Max DD (%)']:>5.1f}% | "
            f"{row['Durum']:<6}"
        )
        print(line)

    print("-" * 110)
    total_sign = "+" if eval_res["total_net_profit"] >= 0 else ""
    print(
        f"{'TOPLAM':<8} | {eval_res['total_initial_capital']:>9,.0f}TL | "
        f"{eval_res['total_final_capital']:>9,.0f}TL | "
        f"{total_sign}{eval_res['total_net_profit']:>10,.0f}TL | "
        f"({eval_res['total_net_profit_pct']:+.2f}%) | "
        f"Gecen: {eval_res['passed_count']}/{eval_res['total_count']} hisse"
    )
    print("=" * 110)
    print(f"Genel Durum: {eval_res['challenge_status']} [{eval_res['passed_count']}/{eval_res['total_count']}]")
    print("=" * 110)
    print()


# ============================================================
# Modul Testi
# ============================================================

if __name__ == "__main__":
    from backtester import Backtester
    from risk_manager import RiskManager
    from strategies.sma_crossover import SmaCrossoverStrategy

    print("=" * 65)
    print("METRICS MODUL TESTI (Phase 6)")
    print("=" * 65)

    # 1. Backtest calistir (SMA Crossover + Risk Manager)
    strategy = SmaCrossoverStrategy(10, 50)
    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    bt = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")

    print("\nTum 6 hisse icin backtest calistiriliyor...")
    results = bt.run_all(strategy, print_table=False)

    # 2. Tek hisse metrik analizi (AKBNK)
    akbnk_res = results["AKBNK.IS"]
    m = calculate_metrics(akbnk_res)

    print(f"\n--- AKBNK Detayli Metrikler ---")
    print(f"  Hisse               : {m.short_name}")
    print(f"  Net Kar / Zarar     : {m.net_profit:+,.2f} TL ({m.net_profit_pct:+.2f}%)")
    print(f"  CAGR (Yillik Getiri): %{m.cagr:.2f}")
    print(f"  Islem Sayisi        : {m.total_trades} (Kazanma: %{m.win_rate:.1f})")
    print(f"  Kazanan / Kaybeden  : {m.winning_trades} / {m.losing_trades}")
    print(f"  Profit Factor       : {m.profit_factor}")
    print(f"  Max Drawdown        : -{m.max_drawdown_tl:,.2f} TL (-%{m.max_drawdown_pct:.2f})")
    print(f"  Max DD Sure         : {m.max_drawdown_duration_bars} bar")
    print(f"  Sharpe Orani        : {m.sharpe_ratio}")
    print(f"  Sortino Orani       : {m.sortino_ratio}")
    print(f"  Calmar Orani        : {m.calmar_ratio}")
    print(f"  Ortalama Islem      : {m.avg_trade_pnl:+,.2f} TL ({m.avg_trade_pct:+.2f}%)")
    print(f"  Payoff Orani        : {m.payoff_ratio:.2f}")
    print(f"  En Buyuk Kar        : +{m.largest_win_pnl:,.2f} TL")
    print(f"  En Buyuk Zarar      : {m.largest_loss_pnl:,.2f} TL")
    print(f"  Cikis Dagilimi      : {m.exit_reasons}")
    print(f"  Benchmark Durumu    : {'PASS' if m.challenge_passed else 'FAIL'}")

    # 3. Toplu ozet tablosu ve challenge degerlendirmesi
    print_metrics_summary(results, strategy.get_name())

    # 4. CSV kaydetme testi
    df_summary = generate_summary_table(results)
    csv_file = save_metrics_to_csv(df_summary)
    print(f"Metrik ozet tablosu kaydedildi: {csv_file}")

    # 5. Markdown rapor testi
    md_report = generate_markdown_report(results, strategy.get_name())
    report_file = RESULTS_DIR / "metrics_report.md"
    report_file.write_text(md_report, encoding="utf-8")
    print(f"Markdown rapor kaydedildi: {report_file}")

    print("\n" + "=" * 65)
    print("Metrics modulu testi basariyla tamamlandi! [OK]")
    print("=" * 65)
