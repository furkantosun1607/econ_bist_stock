"""
BIST Algorithmic Trading Challenge - Visualization Module
==========================================================
Islem sinyalleri, equity egrileri, benchmark karsilastirmalari ve
performans grafiklerini yuksek cozunurlukte gorsellestirir.

Uretilen Grafikler:
1. plot_stock_dashboard():
   - Subplot 1: Fiyat grafigi + BUY/SELL ok isaretleri + trade baglanti cizgileri + islem araligi golgelendirmesi
   - Subplot 2: Equity curve (TL) + Tepe cizgisi (watermark) + Benchmark hedef cizgisi
   - Subplot 3: Islem bazinda PnL bar grafigi (yesil=kar, kirmizi=zarar) + cikis sebebi etiketleri
   - Metrik Bilgi Kutusu: Baslangic/Bitis sermayesi, Net Kar, Benchmark Farki, PASS/FAIL durumu, Win Rate, Max DD

2. plot_benchmark_comparison():
   - Tum 6 hissenin Benchmark vs Strateji Final Sermaye karsilastirmali bar grafigi
   - PASS / FAIL rozetleri ve fark miktarlari
   - Portfoy toplam karsilastirmasi

3. plot_all_equity_curves():
   - Tum 6 hissenin equity egrilerinin ayni grafikte karsilastirmasi

4. plot_all_dashboards():
   - Tum hisseler ve karsilastirma grafiklerini tek seferde results/charts/ altina kaydeder.

Kullanim:
    from visualizer import (
        plot_stock_dashboard,
        plot_benchmark_comparison,
        plot_all_dashboards,
    )

    # Tek hisse paneli
    fig = plot_stock_dashboard(result, save_path="results/charts/AKBNK_dashboard.png")

    # Tum hisselerin toplu grafikleri
    saved_paths = plot_all_dashboards(results)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib
# Headless calisma ortami icin Agg backend
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import (
    CHARTS_DIR,
    INITIAL_CAPITAL,
    get_benchmark,
    get_short_name,
)
from metrics import calculate_metrics

if TYPE_CHECKING:
    from backtester import BacktestResult, Trade


# ============================================================
# Renk Paleti ve Stil Tanimlari
# ============================================================

STYLE = {
    "bg_color": "#ffffff",
    "card_bg": "#f8fafc",
    "text_dark": "#0f172a",
    "text_muted": "#64748b",
    "grid_color": "#e2e8f0",
    "price_line": "#1e293b",
    "sma_fast": "#f59e0b",
    "sma_slow": "#8b5cf6",
    "buy_color": "#16a34a",
    "sell_color": "#dc2626",
    "equity_line": "#2563eb",
    "equity_fill": "#dbeafe",
    "benchmark_line": "#d97706",
    "watermark_line": "#94a3b8",
    "drawdown_fill": "#fee2e2",
    "win_color": "#16a34a",
    "loss_color": "#dc2626",
    "pass_color": "#16a34a",
    "fail_color": "#dc2626",
}


def _apply_plot_style(ax: plt.Axes):
    """Ortak grafik stilini uygular."""
    ax.set_facecolor(STYLE["bg_color"])
    ax.grid(True, linestyle="--", linewidth=0.6, color=STYLE["grid_color"], alpha=0.8)
    ax.tick_params(colors=STYLE["text_muted"], labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(STYLE["grid_color"])
        spine.set_linewidth(0.8)


# ============================================================
# 1. Tek Hisse Detayli Dashboard (3-in-1 Panel)
# ============================================================

def plot_stock_dashboard(
    result: Any,
    save_path: str | Path | None = None,
    dpi: int = 150,
    show: bool = False,
) -> plt.Figure:
    """
    Tek bir hisse icin yayin kalitesinde 3 panelli detayli analiz grafigi uretir.
    
    Paneller:
    1. Fiyat Grafigi + Alis/Satis Isaretleri + Indikatorler + Islem Araliklari
    2. Equity Curve (TL) + Benchmark Seviyesi + Max Peak
    3. Islem PnL Barlari (% ve TL) + Cikis Sebepleri
    
    Args:
        result: backtester.BacktestResult nesnesi
        save_path: Kaydedilecek dosya yolu (None ise varsayilan results/charts/)
        dpi: Cozunurluk (varsayilan: 150)
        show: Ekranda gosterilsin mi (plt.show)
        
    Returns:
        matplotlib.figure.Figure nesnesi
    """
    ticker = getattr(result, "ticker", "STOCK")
    short_name = get_short_name(ticker)
    strategy_name = getattr(result, "strategy_name", "Strategy")
    df = getattr(result, "df", pd.DataFrame())
    trades = getattr(result, "trades", [])
    equity_curve = getattr(result, "equity_curve", pd.Series())
    m = calculate_metrics(result)

    # 3 sub-panel figure
    fig, (ax_price, ax_equity, ax_trades) = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(16, 12),
        gridspec_kw={"height_ratios": [3.0, 1.3, 1.4], "hspace": 0.32},
    )
    fig.patch.set_facecolor(STYLE["bg_color"])

    # ----------------------------------------------------
    # Panel 1: Fiyat ve Islemler
    # ----------------------------------------------------
    _apply_plot_style(ax_price)
    dates = df.index

    # Y-ekseni baslik ve metrik kutusu icin tepe boslugu (headroom)
    p_min = df["Close"].min()
    p_max = df["Close"].max()
    p_range = max(p_max - p_min, 1.0)
    ax_price.set_ylim(p_min * 0.92, p_max * 1.25)

    # Kapanis fiyati cizgisi
    ax_price.plot(
        dates, df["Close"],
        label="Kapanis Fiyati",
        color=STYLE["price_line"],
        linewidth=1.4,
        zorder=2,
    )

    # Varsa SMA indikatörlerini ciz
    for col in df.columns:
        if col.startswith("SMA_"):
            color = STYLE["sma_fast"] if "10" in col or "20" in col else STYLE["sma_slow"]
            ax_price.plot(
                dates, df[col],
                label=col,
                color=color,
                linewidth=1.0,
                linestyle="--",
                alpha=0.75,
                zorder=2,
            )

    # Alis ve satis isaretleri, islem araliklari
    has_buy_label = False
    has_sell_label = False

    for idx, t in enumerate(trades):
        entry_dt = pd.to_datetime(t.entry_date)
        exit_dt = pd.to_datetime(t.exit_date)
        trade_color = STYLE["win_color"] if t.is_winner else STYLE["loss_color"]

        # Islem suresini arka planda golgelendir
        ax_price.axvspan(
            entry_dt, exit_dt,
            color=trade_color,
            alpha=0.08,
            zorder=1,
        )

        # Alis oku (Yesil ▲)
        ax_price.scatter(
            entry_dt, t.entry_price,
            marker="^",
            s=120,
            color=STYLE["buy_color"],
            edgecolors="#ffffff",
            linewidths=1.2,
            zorder=5,
            label="BUY (Alis)" if not has_buy_label else "",
        )
        has_buy_label = True

        # Satis oku (Kirmizi ▼)
        ax_price.scatter(
            exit_dt, t.exit_price,
            marker="v",
            s=120,
            color=STYLE["sell_color"],
            edgecolors="#ffffff",
            linewidths=1.2,
            zorder=5,
            label="SELL (Satis)" if not has_sell_label else "",
        )
        has_sell_label = True

        # Baglanti cizgisi
        ax_price.plot(
            [entry_dt, exit_dt], [t.entry_price, t.exit_price],
            color=trade_color,
            linestyle=":",
            linewidth=1.2,
            alpha=0.8,
            zorder=3,
        )

        # Cikis noktasinda PnL ve Giris/Cikis Fiyati etiketi
        # Cok sayida islem olan hisselerde gorsel kargasa ve ust uste binmeyi onlemek icin
        # onemli islemler (%2+ hareket veya ilk/son islem) ayrintili etiketlenir.
        should_annotate = True
        if len(trades) > 18:
            should_annotate = (abs(t.pnl_pct) >= 2.0) or (idx == 0) or (idx == len(trades) - 1)

        if should_annotate:
            sign = "+" if t.pnl >= 0 else ""
            label_text = f"T{idx+1}: {t.entry_price:.1f}➔{t.exit_price:.1f}\n({sign}{t.pnl_pct:.1f}%)"
            stagger_factor = 1.0 + (idx % 3) * 0.75
            y_offset = p_range * 0.035 * stagger_factor
            if t.is_winner:
                y_pos = min(t.exit_price + y_offset, p_max * 1.10)
            else:
                y_pos = max(t.exit_price - y_offset, p_min * 0.95)

            ax_price.annotate(
                label_text,
                xy=(exit_dt, t.exit_price),
                xytext=(exit_dt, y_pos),
                fontsize=6.8,
                fontweight="bold",
                color=trade_color,
                ha="center",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor=trade_color, alpha=0.88, lw=0.8),
                arrowprops=dict(arrowstyle="->", color=trade_color, lw=0.6),
                zorder=6,
            )

    ax_price.set_ylabel("Fiyat (TL)", fontsize=10, fontweight="semibold", color=STYLE["text_dark"])
    ax_price.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor=STYLE["grid_color"], fontsize=8.5)

    # Baslik ve Metrik Bilgi Kutusu
    status_str = "[PASS]" if m.challenge_passed else "[FAIL]"
    status_color = STYLE["pass_color"] if m.challenge_passed else STYLE["fail_color"]
    title_text = f"{short_name} - Backtest ve Islem Analizi | Strateji: {strategy_name}"
    ax_price.set_title(title_text, fontsize=13, fontweight="bold", color=STYLE["text_dark"], pad=14)

    # Sag ust kose metrik bilgi kutusu
    profit_sign = "+" if m.net_profit >= 0 else ""
    diff_sign = "+" if m.benchmark_diff_tl >= 0 else ""
    info_text = (
        f"Baslangic : {m.initial_capital:>8,.0f} TL\n"
        f"Final     : {m.final_capital:>8,.0f} TL\n"
        f"Net Kar   : {profit_sign}{m.net_profit:>7,.0f} TL ({profit_sign}{m.net_profit_pct:.1f}%)\n"
        f"Benchmark : {m.benchmark_final:>8,.0f} TL\n"
        f"Fark      : {diff_sign}{m.benchmark_diff_tl:>7,.0f} TL  {status_str}\n"
        f"Trades    : {m.total_trades} (Win: %{m.win_rate:.0f}) | MaxDD: -%{m.max_drawdown_pct:.1f}"
    )
    ax_price.text(
        0.985, 0.96, info_text,
        transform=ax_price.transAxes,
        fontsize=8.5,
        fontfamily="monospace",
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=STYLE["card_bg"], edgecolor=status_color, alpha=0.92, lw=1.2),
        zorder=7,
    )

    # ----------------------------------------------------
    # Panel 2: Equity Curve (Sermaye Gelisimi)
    # ----------------------------------------------------
    _apply_plot_style(ax_equity)

    if not equity_curve.empty:
        # Equity cizgisi ve alt dolgusu
        ax_equity.plot(
            dates, equity_curve,
            label="Portfoy Degeri (TL)",
            color=STYLE["equity_line"],
            linewidth=1.6,
            zorder=3,
        )
        ax_equity.fill_between(
            dates, m.initial_capital, equity_curve,
            where=(equity_curve >= m.initial_capital),
            color=STYLE["win_color"],
            alpha=0.15,
            label="Net Kazanc Alani",
            zorder=2,
        )
        ax_equity.fill_between(
            dates, m.initial_capital, equity_curve,
            where=(equity_curve < m.initial_capital),
            color=STYLE["loss_color"],
            alpha=0.15,
            label="Net Kayip Alani",
            zorder=2,
        )

        # Tepe noktasi cizgisi (Watermark Peak)
        peak_equity = equity_curve.cummax()
        ax_equity.plot(
            dates, peak_equity,
            color=STYLE["watermark_line"],
            linestyle=":",
            linewidth=1.0,
            label="Zirve (Peak)",
            zorder=2,
        )

        # Benchmark hedef cizgisi
        ax_equity.axhline(
            m.benchmark_final,
            color=STYLE["benchmark_line"],
            linestyle="--",
            linewidth=1.3,
            label=f"Benchmark Hedefi ({m.benchmark_final:,.0f} TL)",
            zorder=3,
        )

        # Baslangic sermayesi referans cizgisi
        ax_equity.axhline(
            m.initial_capital,
            color=STYLE["text_muted"],
            linestyle="-",
            linewidth=0.8,
            alpha=0.6,
            zorder=2,
        )

    ax_equity.set_ylabel("Sermaye (TL)", fontsize=10, fontweight="semibold", color=STYLE["text_dark"])
    ax_equity.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor=STYLE["grid_color"], fontsize=8.0)

    # ----------------------------------------------------
    # Panel 3: Islem PnL Barlari
    # ----------------------------------------------------
    _apply_plot_style(ax_trades)

    if trades:
        trade_indices = list(range(1, len(trades) + 1))
        pnl_pcts = [t.pnl_pct for t in trades]
        bar_colors = [STYLE["win_color"] if p >= 0 else STYLE["loss_color"] for p in pnl_pcts]

        bars = ax_trades.bar(
            trade_indices, pnl_pcts,
            color=bar_colors,
            width=0.55,
            edgecolor=STYLE["grid_color"],
            linewidth=0.6,
            zorder=3,
        )

        ax_trades.axhline(0, color=STYLE["text_muted"], linewidth=0.8, zorder=2)

        # Bar ust/alt deger etiketleri
        for bar, t in zip(bars, trades):
            height = bar.get_height()
            va = "bottom" if height >= 0 else "top"
            offset = 0.4 if height >= 0 else -0.4
            sign = "+" if t.pnl >= 0 else ""
            ax_trades.annotate(
                f"{sign}{t.pnl_pct:.1f}%\n({sign}{t.pnl:,.0f} TL)",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, offset * 5),
                textcoords="offset points",
                ha="center", va=va,
                fontsize=6.8,
                fontweight="semibold",
                color=STYLE["win_color"] if height >= 0 else STYLE["loss_color"],
            )

        ax_trades.set_xticks(trade_indices)
        rotation_angle = 45 if len(trades) > 18 else 0
        ha_align = "right" if len(trades) > 18 else "center"
        tick_font = 6.2 if len(trades) > 30 else 7.2
        ax_trades.set_xticklabels(
            [f"T{i}\n{trades[i-1].entry_price:.1f}➔{trades[i-1].exit_price:.1f}\n({trades[i-1].exit_reason})" for i in trade_indices],
            fontsize=tick_font,
            rotation=rotation_angle,
            ha=ha_align,
            color=STYLE["text_dark"],
        )
    else:
        ax_trades.text(0.5, 0.5, "Islem Bulunmuyor", ha="center", va="center", color=STYLE["text_muted"])

    ax_trades.set_ylabel("PnL (%)", fontsize=10, fontweight="semibold", color=STYLE["text_dark"])
    ax_trades.set_xlabel("Islem Sirasi, Giris/Cikis Fiyatlari ve Cikis Sebebi", fontsize=10, fontweight="semibold", color=STYLE["text_dark"])

    # X ekseni tarih formatlama (Ust 2 panel icin)
    for ax in [ax_price, ax_equity]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

    # Dosyaya kaydet
    if save_path is None:
        save_path = CHARTS_DIR / f"{short_name}_dashboard.png"
    else:
        save_path = Path(save_path)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())

    if show:
        plt.show()

    plt.close(fig)
    return fig


# ============================================================
# 2. Benchmark Karsilastirma Bar Grafigi (Tum 6 Hisse)
# ============================================================

def plot_benchmark_comparison(
    results: dict[str, Any],
    save_path: str | Path | None = None,
    dpi: int = 150,
    show: bool = False,
) -> plt.Figure:
    """
    Tum 6 hissenin Strateji Final Sermayesi vs Benchmark Hedefini
    karsilastirmali bar grafiginde gosterir.
    
    Args:
        results: dict[ticker, BacktestResult]
        save_path: Kaydedilecek yol (varsayilan: results/charts/benchmark_comparison.png)
        dpi: Cozunurluk
        show: Ekranda gosterilsin mi
    """
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(STYLE["bg_color"])
    _apply_plot_style(ax)

    tickers = list(results.keys())
    stocks = [get_short_name(t) for t in tickers]
    n = len(stocks)

    x = np.arange(n)
    bar_width = 0.36

    strategy_capitals = []
    benchmark_capitals = []
    differences = []
    passed_list = []

    for ticker in tickers:
        m = calculate_metrics(results[ticker])
        strategy_capitals.append(m.final_capital)
        benchmark_capitals.append(m.benchmark_final)
        differences.append(m.benchmark_diff_tl)
        passed_list.append(m.challenge_passed)

    # Barlar
    strategy_colors = [STYLE["pass_color"] if p else STYLE["fail_color"] for p in passed_list]

    bars_strat = ax.bar(
        x - bar_width / 2, strategy_capitals,
        width=bar_width,
        label="Strateji Final Sermaye",
        color=strategy_colors,
        edgecolor=STYLE["grid_color"],
        linewidth=0.8,
        zorder=3,
    )

    bars_bm = ax.bar(
        x + bar_width / 2, benchmark_capitals,
        width=bar_width,
        label="Benchmark Hedef Sermaye",
        color=STYLE["benchmark_line"],
        alpha=0.85,
        edgecolor=STYLE["grid_color"],
        linewidth=0.8,
        zorder=3,
    )

    # 100,000 TL Baslangic sermayesi referansi
    ax.axhline(
        INITIAL_CAPITAL,
        color=STYLE["text_muted"],
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        label=f"Baslangic Sermayesi ({INITIAL_CAPITAL:,.0f} TL)",
        zorder=2,
    )

    # Bar etiketleri ve PASS/FAIL rozetleri
    max_val = max(max(strategy_capitals), max(benchmark_capitals))

    for i in range(n):
        diff = differences[i]
        passed = passed_list[i]
        sign = "+" if diff >= 0 else ""
        badge_text = f"{sign}{diff:,.0f} TL\n[{'PASS' if passed else 'FAIL'}]"
        badge_color = STYLE["pass_color"] if passed else STYLE["fail_color"]

        # Strateji bari uzerine deger
        s_height = strategy_capitals[i]
        ax.annotate(
            f"{s_height:,.0f} TL",
            xy=(x[i] - bar_width / 2, s_height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8, fontweight="bold", color=badge_color,
        )

        # Benchmark bari uzerine deger
        b_height = benchmark_capitals[i]
        ax.annotate(
            f"{b_height:,.0f} TL",
            xy=(x[i] + bar_width / 2, b_height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8, color=STYLE["text_muted"],
        )

        # Grup tepesine PASS/FAIL rozeti
        top_y = max(s_height, b_height) + (max_val * 0.05)
        ax.text(
            x[i], top_y,
            badge_text,
            ha="center", va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color=badge_color,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor=badge_color, alpha=0.9, lw=1.0),
            zorder=5,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(stocks, fontsize=11, fontweight="bold", color=STYLE["text_dark"])
    ax.set_ylabel("Final Sermaye (TL)", fontsize=11, fontweight="semibold", color=STYLE["text_dark"])
    ax.set_ylim(0, max_val * 1.22)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, loc: f"{val:,.0f} TL"))

    passed_count = sum(passed_list)
    total_count = len(stocks)
    overall_status = "CHALLENGE PASSED" if passed_count == total_count else "CHALLENGE FAILED"
    status_color = STYLE["pass_color"] if passed_count == total_count else STYLE["fail_color"]

    ax.set_title(
        f"BIST Challenge - Benchmark Karsilastirmasi | Durum: {overall_status} ({passed_count}/{total_count} Hisse Basarili)",
        fontsize=13, fontweight="bold", color=STYLE["text_dark"], pad=14,
    )
    ax.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor=STYLE["grid_color"], fontsize=9.5)

    if save_path is None:
        save_path = CHARTS_DIR / "benchmark_comparison.png"
    else:
        save_path = Path(save_path)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())

    if show:
        plt.show()

    plt.close(fig)
    return fig


# ============================================================
# 3. Tum Hisseler Birlikte Equity Egrileri Grafigi
# ============================================================

def plot_all_equity_curves(
    results: dict[str, Any],
    save_path: str | Path | None = None,
    dpi: int = 150,
    show: bool = False,
) -> plt.Figure:
    """
    Tum 6 hissenin sermaye degisim egrilerini tek grafikte karsilastirir.
    """
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(STYLE["bg_color"])
    _apply_plot_style(ax)

    colors = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#8b5cf6", "#06b6d4"]

    for i, (ticker, res) in enumerate(results.items()):
        short = get_short_name(ticker)
        equity = getattr(res, "equity_curve", pd.Series())
        if not equity.empty:
            color = colors[i % len(colors)]
            final_cap = equity.iloc[-1]
            sign = "+" if final_cap >= INITIAL_CAPITAL else ""
            pnl_tl = final_cap - INITIAL_CAPITAL
            label_text = f"{short}: {final_cap:,.0f} TL ({sign}{pnl_tl:,.0f} TL)"
            ax.plot(equity.index, equity, label=label_text, color=color, linewidth=1.6, zorder=3)

    # 100k referans cizgisi
    ax.axhline(
        INITIAL_CAPITAL,
        color=STYLE["text_muted"],
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        label=f"Baslangic Sermayesi ({INITIAL_CAPITAL:,.0f} TL)",
        zorder=2,
    )

    ax.set_title(
        "BIST Challenge - Hisselerin Sermaye Degisim Egrileri (Equity Curves)",
        fontsize=13, fontweight="bold", color=STYLE["text_dark"], pad=14,
    )
    ax.set_ylabel("Portfoy Degeri (TL)", fontsize=11, fontweight="semibold", color=STYLE["text_dark"])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, loc: f"{val:,.0f} TL"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.legend(loc="upper left", frameon=True, facecolor="#ffffff", edgecolor=STYLE["grid_color"], fontsize=9.0)

    if save_path is None:
        save_path = CHARTS_DIR / "all_equity_curves.png"
    else:
        save_path = Path(save_path)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())

    if show:
        plt.show()

    plt.close(fig)
    return fig


# ============================================================
# 4. Toplu Grafik Uretim Yoneticisi
# ============================================================

def plot_all_dashboards(
    results: dict[str, Any],
    save_dir: str | Path | None = None,
    dpi: int = 150,
) -> dict[str, Path]:
    """
    Tum hisselerin panellerini ve karsilastirma grafiklerini uretip kaydeder.
    
    Args:
        results: dict[ticker, BacktestResult]
        save_dir: Kayit dizini (varsayilan: results/charts/)
        dpi: Cozunurluk
        
    Returns:
        dict[name, Path]: Olusturulan tum gorsel dosyalari
    """
    if save_dir is None:
        save_dir = CHARTS_DIR
    else:
        save_dir = Path(save_dir)

    save_dir.mkdir(parents=True, exist_ok=True)
    saved_files: dict[str, Path] = {}

    print("\nGrafikler uretiliyor...")

    # 1. Her hisse icin 3-in-1 Dashboard
    for ticker, res in results.items():
        short = get_short_name(ticker)
        path = save_dir / f"{short}_dashboard.png"
        plot_stock_dashboard(res, save_path=path, dpi=dpi)
        saved_files[f"{short}_dashboard"] = path
        print(f"  [OK] {short} Dashboard: {path.name}")

    # 2. Benchmark Karsilastirma Bar Grafigi
    bm_path = save_dir / "benchmark_comparison.png"
    plot_benchmark_comparison(results, save_path=bm_path, dpi=dpi)
    saved_files["benchmark_comparison"] = bm_path
    print(f"  [OK] Benchmark Karsilastirma: {bm_path.name}")

    # 3. Tum Equity Egrileri
    eq_path = save_dir / "all_equity_curves.png"
    plot_all_equity_curves(results, save_path=eq_path, dpi=dpi)
    saved_files["all_equity_curves"] = eq_path
    print(f"  [OK] Toplu Equity Egrileri: {eq_path.name}")

    print(f"Toplam {len(saved_files)} grafik dosyasi olusturuldu.")
    return saved_files


# ============================================================
# Modul Testi
# ============================================================

if __name__ == "__main__":
    from backtester import Backtester
    from risk_manager import RiskManager
    from strategies.sma_crossover import SmaCrossoverStrategy

    print("=" * 65)
    print("VISUALIZER MODUL TESTI (Phase 7)")
    print("=" * 65)

    # 1. Backtest calistir
    strategy = SmaCrossoverStrategy(10, 50)
    rm = RiskManager(stop_loss_pct=0.05, trailing_stop_pct=0.03)
    bt = Backtester(initial_capital=100_000, risk_manager=rm, execution_mode="next_open")

    print("\nBacktest sonuclari aliniyor...")
    results = bt.run_all(strategy, print_table=False)

    # 2. Toplu grafikleri uret
    saved = plot_all_dashboards(results)

    print("\n" + "=" * 65)
    print("Visualizer testi basariyla tamamlandi! [OK]")
    print(f"Kaydedilen dosyalar ({len(saved)} adet):")
    for k, v in saved.items():
        print(f"  - {k}: {v}")
    print("=" * 65)
