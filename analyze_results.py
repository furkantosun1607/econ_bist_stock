"""
Empirical Stock Characteristics & Strategy Performance Analyzer
Used to generate quantitative data for the Phase 9 Final Analysis Report.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtester import Backtester
from config import INITIAL_CAPITAL, RESULTS_DIR, STOCKS, get_short_name
from data_loader import load_stock_data
from indicators import add_adx, add_atr, add_rsi
from metrics import calculate_metrics
from strategies.adaptive_regime import AdaptiveRegimeStrategy
from strategy_base import StrategyBase


def analyze_all_stocks(
    strategy: StrategyBase | None = None,
    stocks: list[str] | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Altı hissenin ampirik piyasa dinamiklerini (volatilite, ATR, ADX, trend gunleri,
    ciro) ve strateji performansini (islemler, kazanma orani, cikis nedenleri, DD)
    analiz eder.

    Args:
        strategy: Test edilecek StrategyBase nesnesi (None ise AdaptiveRegimeStrategy)
        stocks: Test edilecek hisse listesi (None ise STOCKS)
        use_cache: Veri cache'i kullanilsin mi

    Returns:
        pd.DataFrame: Ampirik analiz tablosu
    """
    if strategy is None:
        strategy = AdaptiveRegimeStrategy()

    stocks = stocks or STOCKS
    bt = Backtester(initial_capital=INITIAL_CAPITAL, execution_mode="next_open")

    rows = []

    for ticker in stocks:
        short = get_short_name(ticker)
        df = load_stock_data(ticker, use_cache=use_cache)

        # Indikatorler
        df = add_atr(df, 14)
        df = add_adx(df, 14)
        df = add_rsi(df, 14)

        # Fiyat ve getiri
        p_start = float(df["Close"].iloc[0])
        p_end = float(df["Close"].iloc[-1])
        bh_return = ((p_end / p_start) - 1.0) * 100.0

        # Volatilite
        daily_ret = df["Close"].pct_change().dropna()
        ann_vol = float(daily_ret.std() * np.sqrt(252) * 100.0)
        avg_atr_pct = float((df["ATR_14"] / df["Close"]).mean() * 100.0)

        # Trend gucu (ADX)
        avg_adx = float(df["ADX"].mean())
        trending_pct = float((df["ADX"] > 25).mean() * 100.0)

        # Hacim & Ciro
        avg_turnover = float((df["Volume"] * df["Close"]).mean() / 1e6)  # Milyon TL

        # Backtest
        df_sig = strategy.run(df)
        res = bt.run(df_sig, ticker=ticker, strategy_name=strategy.get_name())
        m = calculate_metrics(res)

        # False breakout analizi (5 gunden az tutup zararla cikanlar)
        quick_losses = sum(1 for t in res.trades if t.bars_held <= 5 and t.pnl < 0)

        # Cikis sebepleri dagilimi
        decisions: list[str] = []
        for trade in res.trades:
            if trade.exit_reason == "signal" and "Exit_Reason" in df_sig.columns:
                loc = df_sig.index.get_loc(trade.exit_date)
                decision_bar = max(0, loc - 1)
                reason = str(df_sig.iloc[decision_bar]["Exit_Reason"])
                decisions.append(reason)
            else:
                decisions.append(trade.exit_reason)

        n_atr = decisions.count("close_atr_stop")
        n_recovery = decisions.count("mean_reversion_exit")

        rows.append({
            "Hisse": short,
            "B&H Getiri (%)": round(bh_return, 1),
            "Yillik Volatilite (%)": round(ann_vol, 1),
            "Ort ATR (%)": round(avg_atr_pct, 2),
            "Ort ADX": round(avg_adx, 1),
            "Trend Gun (%)": round(trending_pct, 1),
            "Ort Ciro (M TL)": round(avg_turnover, 1),
            "Trades": res.total_trades,
            "Win Rate (%)": m.win_rate,
            "Net Kar (TL)": m.net_profit,
            "Benchmark Fark (TL)": m.benchmark_diff_tl,
            "Durum": "PASS" if m.challenge_passed else "FAIL",
            "ATR Kapanis Cikisi": n_atr,
            "Ortalamaya Donus Cikisi": n_recovery,
            "Kisa Sureli Zararli Islem": quick_losses,
            "Piyasada Gecen Gun (%)": round(float(res.df.Position.mean() * 100.0), 1),
            "Max DD (%)": m.max_drawdown_pct,
        })

    df_analysis = pd.DataFrame(rows)
    return df_analysis


def generate_analysis_markdown(
    df_analysis: pd.DataFrame, strategy_name: str = "Adaptive_Regime"
) -> str:
    """Ampirik analiz tablosunu markdown formatinda sunar."""
    lines = [
        f"## Ampirik Piyasa Karakteristikleri ve Strateji Analizi: {strategy_name}",
        "",
        "| Hisse | B&H % | Volatilite % | ATR % | ADX | Trend % | Ciro (M TL) | "
        "Trades | Win% | Net Kar (TL) | Hedef Fark (TL) | Durum | ATR Çıkış | Dönüş Çıkış | "
        "Sahte Kırılım | Pazar % | Max DD % |",
        "|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in df_analysis.iterrows():
        status_icon = "PASS" if r["Durum"] == "PASS" else "FAIL"
        diff_str = f"{r['Benchmark Fark (TL)']:+,.2f} TL"
        profit_str = f"{r['Net Kar (TL)']:+,.2f} TL"
        lines.append(
            f"| **{r['Hisse']}** | %{r['B&H Getiri (%)']:.1f} | %{r['Yillik Volatilite (%)']:.1f} | "
            f"%{r['Ort ATR (%)']:.2f} | {r['Ort ADX']:.1f} | %{r['Trend Gun (%)']:.1f} | "
            f"{r['Ort Ciro (M TL)']:,.1f} M | {r['Trades']} | %{r['Win Rate (%)']:.1f} | "
            f"{profit_str} | {diff_str} | {status_icon} | {r['ATR Kapanis Cikisi']} | "
            f"{r['Ortalamaya Donus Cikisi']} | {r['Kisa Sureli Zararli Islem']} | "
            f"%{r['Piyasada Gecen Gun (%)']:.1f} | -%{r['Max DD (%)']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Ampirik Piyasa Karakteristikleri & Strateji Analiz Araci",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="adaptive_regime",
        help="Analiz edilecek strateji (adaptive_regime, sma_crossover)",
    )
    parser.add_argument(
        "--save-csv",
        action="store_true",
        default=True,
        help="Sonuclari results/empirical_analysis.csv dosyasina kaydet",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Ozel CSV cikti dosyasi yolu",
    )
    args = parser.parse_args()

    from runner import get_strategy
    strategy = get_strategy(args.strategy)
    df = analyze_all_stocks(strategy=strategy)

    print()
    print("=" * 110)
    print(f"AMPIRIK PIYASA VE STRATEJI ANALIZI: {strategy.get_name()}")
    print("=" * 110)
    print(df.to_string(index=False))
    print("=" * 110)

    if args.save_csv:
        csv_path = Path(args.output_csv) if args.output_csv else RESULTS_DIR / "empirical_analysis.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
        print(f"\n[OK] Analiz tablosu kaydedildi: {csv_path}")


if __name__ == "__main__":
    main()
