"""Chronological evaluation of a frozen strategy, without parameter search.

2025 is the development period. 2026 is reported separately; whole-period
challenge results are retrospective, not independent out-of-sample evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtester import Backtester
from config import DATA_DIR, END_DATE, INITIAL_CAPITAL, RESULTS_DIR, STOCKS, get_short_name
from data_loader import load_stock_data
from risk_manager import RiskManager
from strategies.sma_crossover import SmaCrossoverStrategy
from strategy_base import StrategyBase


def evaluate_window(
    signals: pd.DataFrame,
    ticker: str,
    label: str,
    start: str | None = None,
    end: str | None = None,
    risk_manager: RiskManager | None = None,
    commission: float = 0.0,
    slippage: float = 0.0,
) -> dict[str, Any]:
    """Reset cash per window, retaining historical indicators and one decision bar.

    The preceding close can place an order for the first evaluation open.
    There is no execution or P&L on this extra observation row.
    """
    mask = pd.Series(True, index=signals.index)
    if start is not None:
        mask &= signals.index >= pd.Timestamp(start)
    if end is not None:
        mask &= signals.index < pd.Timestamp(end)
    positions = mask.to_numpy().nonzero()[0]
    if len(positions) < 2:
        raise ValueError(f"Insufficient observations for {ticker}: {label}")
    first, last = int(positions[0]), int(positions[-1])
    frame = signals.iloc[max(0, first - 1):last + 1].copy()
    result = Backtester(
        risk_manager=risk_manager,
        execution_mode="next_open",
        commission_rate=commission,
        slippage_rate=slippage,
    ).run(frame, ticker=ticker, strategy_name=label)
    first_open = float(signals.iloc[first]["Open"])
    last_close = float(signals.iloc[last]["Close"])
    shares = int(INITIAL_CAPITAL / (first_open * (1 + slippage) * (1 + commission)))
    buy_hold = (
        INITIAL_CAPITAL
        - shares * first_open * (1 + slippage) * (1 + commission)
        + shares * last_close * (1 - slippage) * (1 - commission)
    )
    # Include starting capital so an opening loss is included in drawdown.
    equity = pd.Series([INITIAL_CAPITAL, *result.equity_curve.to_list()])
    drawdown = (1 - equity / equity.cummax()).max() * 100
    return {
        "stock": get_short_name(ticker),
        "strategy": label,
        "start": signals.index[first].date().isoformat(),
        "end": signals.index[last].date().isoformat(),
        "bars": len(positions),
        "final_capital": result.final_capital,
        "return_pct": result.total_net_profit_pct,
        "trades": result.total_trades,
        "max_drawdown_pct": round(drawdown, 2),
        "buy_hold_final": round(buy_hold, 2),
        "excess_vs_buy_hold_tl": round(result.final_capital - buy_hold, 2),
        "commission_per_side": commission,
        "slippage_per_side": slippage,
    }


def run_validation(
    strategy: StrategyBase,
    risk_manager: RiskManager | None = None,
    all_data: dict[str, pd.DataFrame] | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Evaluate fixed rules once; never choose parameters using evaluation scores."""
    if all_data is None:
        all_data = {ticker: load_stock_data(ticker) for ticker in STOCKS}
    rows = []
    baseline = SmaCrossoverStrategy(10, 50)
    windows = [
        ("development_2025", None, "2026-01-01"),
        ("holdout_2026", "2026-01-01", None),
        ("holdout_2026_H1", "2026-01-01", "2026-07-01"),
        ("holdout_2026_H2", "2026-07-01", None),
        ("full_retrospective", None, None),
    ]
    for ticker, data in all_data.items():
        for candidate, rm in [
            (strategy, risk_manager),
            (baseline, RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)),
        ]:
            signals = candidate.run(data)
            for period, start, end in windows:
                row = evaluate_window(signals, ticker, candidate.get_name(), start, end, rm)
                rows.append({"period": period, **row})
            row = evaluate_window(
                signals,
                ticker,
                candidate.get_name(),
                "2026-01-01",
                risk_manager=rm,
                commission=0.001,
                slippage=0.001,
            )
            rows.append({"period": "holdout_2026_cost_stress", **row})
    summary = pd.DataFrame(rows)
    dest = Path(output_dir) if output_dir is not None else RESULTS_DIR / "validation"
    dest.mkdir(parents=True, exist_ok=True)
    summary.to_csv(dest / "summary.csv", index=False)
    manifest = {
        "strategy": strategy.get_name(),
        "parameters": strategy.get_params(),
        "risk": risk_manager.get_params() if risk_manager else "strategy signals",
        "development_end_exclusive": "2026-01-01",
        "execution": "next_open",
        "position_sizing": "100% available cash, integer shares, long/cash",
        "limitations": [
            "2025 was used for strategy development; full-period results are in-sample in part.",
            "2026 is a historical chronological holdout, not live forward performance.",
            "Signals retain historical state; each window resets cash and liquidates at its end.",
            "Cached adjusted OHLCV source has not been independently authenticated.",
        ],
        "data": {},
    }
    for ticker, frame in all_data.items():
        cache = DATA_DIR / f"{get_short_name(ticker)}_ohlcv.csv"
        manifest["data"][ticker] = {
            "bars": len(frame),
            "start": frame.index.min().isoformat(),
            "end": frame.index.max().isoformat(),
            "cache_sha256": (
                hashlib.sha256(cache.read_bytes()).hexdigest() if cache.exists() else None
            ),
            "coverage": frame.attrs.get("data_coverage", {}),
        }
    incomplete = [
        ticker
        for ticker, frame in all_data.items()
        if frame.index.max() < pd.Timestamp(END_DATE)
    ]
    if incomplete:
        manifest["limitations"].append(
            f"Requested inclusive endpoint {END_DATE} is missing for: {', '.join(incomplete)}."
        )
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    lines = [
        "# Kronolojik strateji doğrulaması",
        "",
        f"Strateji: **{strategy.get_name()}**. Parametreler: `{strategy.get_params()}`.",
        "",
        "2025 geliştirme dönemidir. 2026 ayrı tarihsel değerlendirmedir. Tam dönem sonucu "
        "bağımsız ileri test sayılmaz. Her alt dönemde hesap 100.000 TL ile yeniden başlar; "
        "göstergeler geçmiş veriyi korur. Önceki kapanış sinyali ilk açılışta uygulanabilir. "
        "Son kapanışta açık pozisyon tasfiye edilir.",
        "",
        "Maliyet stresi: her yönde %0,10 komisyon + %0,10 kayma. Al-tut aynı maliyetleri içerir. "
        "Benchmark hedefleri tam dönem içindir; alt dönemlere PASS/FAIL uygulanmaz.",
        "",
        "| Dönem | Hisse | Strateji | Final TL | Getiri % | İşlem | Max DD % | Al-tut TL |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | {row['stock']} | {row['strategy']} | "
            f"{row['final_capital']:,.2f} | {row['return_pct']:.2f} | {row['trades']} | "
            f"{row['max_drawdown_pct']:.2f} | {row['buy_hold_final']:,.2f} |"
        )
    lines += [
        "",
        "Yerel verinin kaynağı bağımsız doğrulanmamıştır. Gerçek tarih kapsamı ve "
        "dosya SHA-256 değerleri `manifest.json` içindedir. 1 Ekim verisi eksikse "
        "challenge teslimi tam dönem olarak onaylanamaz.",
    ]
    (dest / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="BIST Challenge - Kronolojik Strateji Dogrulamasi (Holdout / Cost Stress)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="adaptive_regime",
        help="Test edilecek strateji (adaptive_regime, sma_crossover)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Cikti dizini (varsayilan: results/validation/)",
    )
    args = parser.parse_args()

    from runner import get_strategy
    strategy = get_strategy(args.strategy)
    result = run_validation(strategy, output_dir=args.output_dir)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
