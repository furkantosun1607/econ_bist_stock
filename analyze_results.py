"""
Empirical Stock Characteristics & Strategy Performance Analyzer
Used to generate quantitative data for the Phase 9 Final Analysis Report.
"""

import numpy as np
import pandas as pd
from config import STOCKS, get_short_name, BENCHMARKS, INITIAL_CAPITAL
from data_loader import load_stock_data
from indicators import add_atr, add_adx, add_rsi, add_sma
from strategies.sma_crossover import SmaCrossoverStrategy
from risk_manager import RiskManager
from backtester import Backtester
from metrics import calculate_metrics

def analyze_all_stocks():
    strategy = SmaCrossoverStrategy(10, 50)
    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    bt = Backtester(initial_capital=INITIAL_CAPITAL, risk_manager=rm, execution_mode="next_open")
    
    rows = []
    
    for ticker in STOCKS:
        short = get_short_name(ticker)
        df = load_stock_data(ticker, use_cache=True)
        
        # Indikatorler
        df = add_atr(df, 14)
        df = add_adx(df, 14)
        df = add_rsi(df, 14)
        
        # Fiyat ve getiri
        p_start = df["Close"].iloc[0]
        p_end = df["Close"].iloc[-1]
        bh_return = ((p_end / p_start) - 1) * 100
        
        # Volatilite
        daily_ret = df["Close"].pct_change().dropna()
        ann_vol = daily_ret.std() * np.sqrt(252) * 100
        avg_atr_pct = (df["ATR_14"] / df["Close"]).mean() * 100
        
        # Trend gucu (ADX)
        avg_adx = df["ADX"].mean()
        trending_pct = (df["ADX"] > 25).mean() * 100
        
        # Hacim
        avg_vol = df["Volume"].mean()
        avg_turnover = (df["Volume"] * df["Close"]).mean() / 1e6 # Milyon TL
        
        # Backtest
        df_sig = strategy.run(df)
        res = bt.run(df_sig, ticker=ticker, strategy_name="SMA_Crossover")
        m = calculate_metrics(res)
        
        # False breakout analizi (5 gunden az tutup zararla cikanlar)
        quick_losses = sum(1 for t in res.trades if t.bars_held <= 5 and t.pnl < 0)
        
        # Cikis sebepleri
        n_stop = res.trades_df["exit_reason"].value_counts().get("stop_loss", 0) if not res.trades_df.empty else 0
        n_trail = res.trades_df["exit_reason"].value_counts().get("trailing_stop", 0) if not res.trades_df.empty else 0
        n_sig = res.trades_df["exit_reason"].value_counts().get("signal", 0) if not res.trades_df.empty else 0
        
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
            "Stop-Loss Cikis": n_stop,
            "Trailing Cikis": n_trail,
            "Sinyal Cikis": n_sig,
            "False Breakouts": quick_losses,
        })
        
    df_analysis = pd.DataFrame(rows)
    return df_analysis

if __name__ == "__main__":
    df = analyze_all_stocks()
    print(df.to_string(index=False))
