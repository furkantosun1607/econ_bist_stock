"""
BIST Algorithmic Trading Challenge - Main Strategy Runner
==========================================================
Tum sistemi birlestiren ve 6 hisse uzerinde end-to-end calistiran ana calistirici (runner).

Akis:
1. Hisse listesini ve parametreleri al (config / CLI)
2. Her hisse icin:
   a. Veriyi yukle (data_loader)
   b. Stratejiyi calistir ve sinyalleri uret (strategy.run)
   c. Backtesti yurut (backtester.run - risk manager entegreli)
   d. Metrikleri hesapla (metrics.calculate_metrics)
   e. Islemleri CSV'ye kaydet (results/trades/)
   f. Grafikleri uret ve kaydet (results/charts/)
3. Portfoy metriklerini ve Benchmark karsilastirmasini degerlendir (evaluate_challenge)
4. Ozet tabloyu ve markdown raporunu kaydet (results/)
5. Konsola detayli PASS / FAIL ozetini bas

Kullanim:
    # Python icinden:
    from runner import run_pipeline, get_strategy
    from strategies.adaptive_regime import AdaptiveRegimeStrategy

    # Varsayilan Adaptive Regime stratejisi (kapanis bazli 5x ATR trailing exit):
    strategy = AdaptiveRegimeStrategy()
    results, challenge_eval, df_summary = run_pipeline(strategy, execution_mode="next_open")

    # Veya alternatif SMA Crossover referansi:
    from strategies.sma_crossover import SmaCrossoverStrategy
    from risk_manager import RiskManager
    sma = SmaCrossoverStrategy(fast_period=10, slow_period=50)
    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    results, challenge_eval, df_summary = run_pipeline(sma, risk_manager=rm)

    # Terminalden:
    python runner.py                    # Varsayilan: adaptive_regime, next_open
    python runner.py --no-charts        # Hizli calisma
    python runner.py --strategy sma_crossover --fast 10 --slow 50 --stop-loss 0.05 --trailing-stop 0.03
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from backtester import BacktestResult, Backtester
from config import (
    CHARTS_DIR,
    COMMISSION_RATE,
    INITIAL_CAPITAL,
    RESULTS_DIR,
    SLIPPAGE_RATE,
    STOCKS,
    TRADES_DIR,
    get_benchmark,
    get_short_name,
)
from data_loader import load_stock_data
from metrics import (
    calculate_metrics,
    evaluate_challenge,
    generate_markdown_report,
    generate_summary_table,
    print_metrics_summary,
    save_metrics_to_csv,
)
from risk_manager import RiskManager
from strategies.sma_crossover import SmaCrossoverStrategy
from strategies.adaptive_regime import AdaptiveRegimeStrategy
from strategy_base import StrategyBase
from visualizer import (
    plot_all_dashboards,
    plot_benchmark_comparison,
    plot_stock_dashboard,
)


# ============================================================
# Strateji Kayit Defteri (Registry)
# ============================================================

STRATEGIES: dict[str, type[StrategyBase]] = {
    "adaptive_regime": AdaptiveRegimeStrategy,
    "sma_crossover": SmaCrossoverStrategy,
}


def register_strategy(name: str, strategy_cls: type[StrategyBase]):
    """Yeni bir stratejiyi runner sistemine kaydeder."""
    STRATEGIES[name] = strategy_cls


def get_strategy(name: str, **params) -> StrategyBase:
    """Isim ve parametrelere gore strateji nesnesi olusturur."""
    name_lower = name.lower()
    if name_lower not in STRATEGIES:
        avail = list(STRATEGIES.keys())
        raise ValueError(f"Bilinmeyen strateji: '{name}'. Mevcut stratejiler: {avail}")
    return STRATEGIES[name_lower](**params)


# ============================================================
# Ana Pipeline Calistirici
# ============================================================

def run_pipeline(
    strategy: StrategyBase,
    risk_manager: RiskManager | None = None,
    stocks: list[str] | None = None,
    initial_capital: float = INITIAL_CAPITAL,
    commission_rate: float = COMMISSION_RATE,
    slippage_rate: float = SLIPPAGE_RATE,
    execution_mode: str = "next_open",
    close_at_end: bool = True,
    save_charts: bool = True,
    save_trades: bool = True,
    save_metrics: bool = True,
    print_summary: bool = True,
    use_cache: bool = True,
) -> tuple[dict[str, BacktestResult], dict[str, Any], pd.DataFrame]:
    """
    Belirtilen strateji ve risk yoneticisi ile 6 hissenin tamaminda
    ucuca calisan tam analiz pipeline'i.
    
    Args:
        strategy: StrategyBase alt sinifi
        risk_manager: RiskManager nesnesi (None ise risk yonetimi olmadan calisir)
        stocks: Test edilecek hisseler (None ise config.STOCKS)
        initial_capital: Hisse basina baslangic sermayesi (TL)
        commission_rate: Komisyon orani
        slippage_rate: Slippage orani
        execution_mode: "next_open" (onerilen) veya "same_close"
        close_at_end: Son bar kapanisinda acik pozisyonu kapat
        save_charts: Grafikler results/charts/ altina kaydedilsin mi
        save_trades: Islem loglari results/trades/ altina kaydedilsin mi
        save_metrics: Metrik CSV ve MD raporu kaydedilsin mi
        print_summary: Konsola formatli ozet tablosu basilsin mi
        use_cache: Veri cache'i kullanilsin mi
        
    Returns:
        (results_dict, challenge_eval_dict, summary_dataframe)
    """
    stocks = stocks or STOCKS
    strategy_name = strategy.get_name()
    if isinstance(strategy, AdaptiveRegimeStrategy) and execution_mode != "next_open":
        raise ValueError("AdaptiveRegimeStrategy requires next_open execution.")

    if print_summary:
        print("=" * 70)
        print(f"BIST TRADING CHALLENGE RUNNER: {strategy_name}")
        print("=" * 70)
        print(f"  Hisseler         : {', '.join([get_short_name(s) for s in stocks])}")
        print(f"  Baslangic Sermaye: {initial_capital:,.0f} TL (Hisse basina)")
        print(f"  Emir Modu        : {execution_mode}")
        if risk_manager:
            mechanisms = risk_manager.get_active_mechanisms()
            print(f"  Risk Yonetimi    : {', '.join(mechanisms)}")
        else:
            print("  Risk Yonetimi    : Strateji sinyalleri (Adaptive: kapanis bazli ATR cikisi)")
        print("=" * 70)

    # 1. Backtester Motorunu Hazirla
    bt = Backtester(
        initial_capital=initial_capital,
        risk_manager=risk_manager,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        execution_mode=execution_mode,
        close_at_end=close_at_end,
    )

    # 2. Her hisse icin veri yukle, sinyal uret, backtest calistir
    results: dict[str, BacktestResult] = {}

    for ticker in stocks:
        short = get_short_name(ticker)
        if print_summary:
            print(f"\n>> [{short}] Analiz ediliyor...")

        # a. Veriyi yukle
        df = load_stock_data(ticker, use_cache=use_cache)

        # b. Stratejiyi calistir ve sinyalleri uret
        df_signals = strategy.run(df)

        # c. Backtest calistir
        res = bt.run(df_signals, ticker=ticker, strategy_name=strategy_name)
        results[ticker] = res

        # d. Islemleri kaydet
        if save_trades:
            trade_file = res.save_trades()
            if print_summary:
                print(f"   Trade log kaydedildi: {trade_file.name} ({res.total_trades} islem)")

    # 3. Metrik ve Challenge Degerlendirmesi
    df_summary = generate_summary_table(results)
    challenge_eval = evaluate_challenge(results)

    # 4. Rapor ve CSV Kayitlari
    if save_metrics:
        csv_path = save_metrics_to_csv(df_summary)
        md_content = generate_markdown_report(results, strategy_name=strategy_name)
        md_content += ("\n\n## Calistirma Ayarlari\n\n"
                       f"- Parametreler: `{strategy.get_params()}`\n"
                       f"- Emir modu: `{execution_mode}`\n"
                       f"- Komisyon: {commission_rate}; kayma: {slippage_rate}\n"
                       f"- Harici risk yoneticisi: `{risk_manager}`\n")
        md_path = RESULTS_DIR / "metrics_report.md"
        md_path.write_text(md_content, encoding="utf-8")
        metadata = {
            "strategy": strategy_name, "params": strategy.get_params(),
            "execution_mode": execution_mode, "initial_capital": initial_capital,
            "commission_rate": commission_rate, "slippage_rate": slippage_rate,
            "risk_manager": risk_manager.get_params() if risk_manager else None,
            "data": {ticker: {"coverage": res.df.attrs.get("data_coverage", {}),
                               "provenance": res.df.attrs.get("data_provenance", {})}
                     for ticker, res in results.items()},
        }
        (RESULTS_DIR / "run_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        if print_summary:
            print(f"\n[OK] Metrik ozetleri kaydedildi: {csv_path.name}, {md_path.name}")

    # 5. Grafikleri Uret ve Kaydet
    if save_charts:
        saved_charts = plot_all_dashboards(results)
        if print_summary:
            print(f"[OK] {len(saved_charts)} grafik results/charts/ altina kaydedildi.")

    # 6. Konsol Ozeti
    if print_summary:
        print_metrics_summary(results, strategy_name=strategy_name)

    return results, challenge_eval, df_summary


# ============================================================
# CLI Giris Noktasi
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """CLI parametre parser'ini olusturur."""
    parser = argparse.ArgumentParser(
        description="BIST Algorithmic Trading Challenge - Strateji Calistirici",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--strategy", type=str, default="adaptive_regime",
        choices=list(STRATEGIES.keys()),
        help="Calistirilacak strateji adi",
    )
    parser.add_argument(
        "--fast", type=int, default=10,
        help="Hizli hareketli ortalama periyodu (SMA Crossover icin)",
    )
    parser.add_argument(
        "--slow", type=int, default=50,
        help="Yavas hareketli ortalama periyodu (SMA Crossover icin)",
    )
    parser.add_argument(
        "--stop-loss", type=float, default=None,
        help="Ek stop-loss (SMA varsayilan %%5; adaptive varsayilan kapali; 0=kapali)",
    )
    parser.add_argument(
        "--trailing-stop", type=float, default=None,
        help="Ek trailing stop (SMA varsayilan %%3; adaptive ATR sinyali kullanir; 0=kapali)",
    )
    parser.add_argument(
        "--max-holding-days", type=int, default=None,
        help="Maksimum pozisyon suresi (gun)",
    )
    parser.add_argument(
        "--mode", type=str, default="next_open",
        choices=["next_open", "same_close"],
        help="Emir gerceklesme modu",
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="Grafik uretimini atla (hizli test icin)",
    )
    parser.add_argument(
        "--no-trades", action="store_true",
        help="Islem CSV kayitlarini atla",
    )
    parser.add_argument(
        "--force-download", action="store_true",
        help="Cache'i yoksay ve verileri yeniden indir",
    )
    return parser


def main():
    """CLI ana calistirma fonksiyonu."""
    parser = build_parser()
    args = parser.parse_args()
    if args.strategy == "adaptive_regime" and args.mode != "next_open":
        parser.error("adaptive_regime sadece --mode next_open ile calisir.")

    # Strateji nesnesini olustur
    if args.strategy == "sma_crossover":
        strategy = SmaCrossoverStrategy(fast_period=args.fast, slow_period=args.slow)
    else:
        strategy = get_strategy(args.strategy)

    # Risk yoneticisi olustur
    stop_loss = args.stop_loss
    trailing_stop = args.trailing_stop
    if args.strategy == "sma_crossover":
        stop_loss = .05 if stop_loss is None else stop_loss
        trailing_stop = .03 if trailing_stop is None else trailing_stop
    stop_loss = stop_loss if stop_loss is not None and stop_loss > 0 else None
    trailing_stop = trailing_stop if trailing_stop is not None and trailing_stop > 0 else None

    rm = None
    if stop_loss is not None or trailing_stop is not None or args.max_holding_days is not None:
        rm = RiskManager(
            stop_loss_pct=stop_loss,
            trailing_stop_pct=trailing_stop,
            max_holding_days=args.max_holding_days,
        )

    # Pipeline'i calistir
    results, challenge_eval, df_summary = run_pipeline(
        strategy=strategy,
        risk_manager=rm,
        execution_mode=args.mode,
        save_charts=not args.no_charts,
        save_trades=not args.no_trades,
        use_cache=not args.force_download,
    )

    # Pipeline basariyla calisti
    sys.exit(0)


if __name__ == "__main__":
    main()
