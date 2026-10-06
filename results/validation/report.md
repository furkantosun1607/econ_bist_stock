# Kronolojik strateji doğrulaması

Strateji: **Adaptive_Regime**. Parametreler: `{'fast_period': 15, 'slow_period': 50, 'rsi_period': 3, 'mean_period': 10, 'atr_period': 14, 'warmup_period': 50, 'cooldown_bars': 1, 'oversold': 20.0, 'pullback': 50.0, 'overbought': 70.0, 'atr_multiplier': 3.5, 'profit_atr_multiplier': 2.3, 'profit_threshold': 0.2, 'stop_loss_pct': 0.08, 'exit_on_slow_break': True}`.

2025 geliştirme dönemidir. 2026 ayrı tarihsel değerlendirmedir. Tam dönem sonucu bağımsız ileri test sayılmaz. Her alt dönemde hesap 100.000 TL ile yeniden başlar; göstergeler geçmiş veriyi korur. Önceki kapanış sinyali ilk açılışta uygulanabilir. Son kapanışta açık pozisyon tasfiye edilir.

Maliyet stresi: her yönde %0,10 komisyon + %0,10 kayma. Al-tut aynı maliyetleri içerir. Benchmark hedefleri tam dönem içindir; alt dönemlere PASS/FAIL uygulanmaz.

| Dönem | Hisse | Strateji | Final TL | Getiri % | İşlem | Max DD % | Al-tut TL |
|---|---|---|---:|---:|---:|---:|---:|
| development_2025 | AKBNK | Adaptive_Regime | 106,575.48 | 6.58 | 17 | 15.79 | 109,025.23 |
| holdout_2026 | AKBNK | Adaptive_Regime | 120,810.54 | 20.81 | 22 | 16.94 | 98,641.29 |
| holdout_2026_H1 | AKBNK | Adaptive_Regime | 122,101.67 | 22.10 | 14 | 15.05 | 113,361.29 |
| holdout_2026_H2 | AKBNK | Adaptive_Regime | 99,330.72 | -0.67 | 9 | 10.85 | 87,360.90 |
| full_retrospective | AKBNK | Adaptive_Regime | 129,290.17 | 29.29 | 38 | 16.95 | 108,005.86 |
| holdout_2026_cost_stress | AKBNK | Adaptive_Regime | 110,630.19 | 10.63 | 22 | 22.98 | 98,247.65 |
| development_2025 | AKBNK | SMA_Crossover | 110,871.78 | 10.87 | 2 | 5.37 | 109,025.23 |
| holdout_2026 | AKBNK | SMA_Crossover | 92,345.80 | -7.65 | 3 | 7.65 | 98,641.29 |
| holdout_2026_H1 | AKBNK | SMA_Crossover | 95,065.30 | -4.93 | 2 | 4.93 | 113,361.29 |
| holdout_2026_H2 | AKBNK | SMA_Crossover | 97,139.80 | -2.86 | 1 | 2.86 | 87,360.90 |
| full_retrospective | AKBNK | SMA_Crossover | 102,388.55 | 2.39 | 5 | 9.38 | 108,005.86 |
| holdout_2026_cost_stress | AKBNK | SMA_Crossover | 91,204.26 | -8.80 | 3 | 8.80 | 98,247.65 |
| development_2025 | ASELS | Adaptive_Regime | 187,092.59 | 87.09 | 11 | 19.04 | 317,932.36 |
| holdout_2026 | ASELS | Adaptive_Regime | 186,304.00 | 86.30 | 13 | 17.52 | 145,039.50 |
| holdout_2026_H1 | ASELS | Adaptive_Regime | 162,298.75 | 62.30 | 6 | 17.52 | 148,703.00 |
| holdout_2026_H2 | ASELS | Adaptive_Regime | 114,783.00 | 14.78 | 7 | 7.78 | 97,543.50 |
| full_retrospective | ASELS | Adaptive_Regime | 349,082.44 | 249.08 | 23 | 19.04 | 461,717.97 |
| holdout_2026_cost_stress | ASELS | Adaptive_Regime | 176,902.53 | 76.90 | 13 | 17.85 | 144,446.13 |
| development_2025 | ASELS | SMA_Crossover | 97,184.37 | -2.82 | 1 | 2.82 | 317,932.36 |
| holdout_2026 | ASELS | SMA_Crossover | 104,506.40 | 4.51 | 1 | 1.37 | 145,039.50 |
| holdout_2026_H1 | ASELS | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 148,703.00 |
| holdout_2026_H2 | ASELS | SMA_Crossover | 104,506.40 | 4.51 | 1 | 1.37 | 97,543.50 |
| full_retrospective | ASELS | SMA_Crossover | 101,570.37 | 1.57 | 2 | 2.82 | 461,717.97 |
| holdout_2026_cost_stress | ASELS | SMA_Crossover | 104,098.63 | 4.10 | 1 | 1.57 | 144,446.13 |
| development_2025 | TUPRS | Adaptive_Regime | 135,821.52 | 35.82 | 15 | 14.60 | 142,429.06 |
| holdout_2026 | TUPRS | Adaptive_Regime | 142,084.29 | 42.08 | 8 | 13.62 | 216,027.22 |
| holdout_2026_H1 | TUPRS | Adaptive_Regime | 110,421.06 | 10.42 | 7 | 11.78 | 128,345.82 |
| holdout_2026_H2 | TUPRS | Adaptive_Regime | 128,723.67 | 28.72 | 1 | 8.21 | 168,281.50 |
| full_retrospective | TUPRS | Adaptive_Regime | 193,067.15 | 93.07 | 23 | 14.64 | 307,855.17 |
| holdout_2026_cost_stress | TUPRS | Adaptive_Regime | 137,622.59 | 37.62 | 8 | 16.00 | 215,194.49 |
| development_2025 | TUPRS | SMA_Crossover | 90,435.45 | -9.56 | 3 | 9.77 | 142,429.06 |
| holdout_2026 | TUPRS | SMA_Crossover | 117,443.55 | 17.44 | 2 | 3.28 | 216,027.22 |
| holdout_2026_H1 | TUPRS | SMA_Crossover | 102,677.44 | 2.68 | 1 | 2.11 | 128,345.82 |
| holdout_2026_H2 | TUPRS | SMA_Crossover | 114,381.58 | 14.38 | 1 | 1.22 | 168,281.50 |
| full_retrospective | TUPRS | SMA_Crossover | 106,241.69 | 6.24 | 5 | 9.77 | 307,855.17 |
| holdout_2026_cost_stress | TUPRS | SMA_Crossover | 116,520.47 | 16.52 | 2 | 3.66 | 215,194.49 |
| development_2025 | TCELL | Adaptive_Regime | 83,149.68 | -16.85 | 23 | 24.08 | 103,900.50 |
| holdout_2026 | TCELL | Adaptive_Regime | 107,343.18 | 7.34 | 18 | 13.03 | 102,779.40 |
| holdout_2026_H1 | TCELL | Adaptive_Regime | 101,883.41 | 1.88 | 10 | 13.03 | 114,859.10 |
| holdout_2026_H2 | TCELL | Adaptive_Regime | 105,358.52 | 5.36 | 8 | 2.45 | 89,479.70 |
| full_retrospective | TCELL | Adaptive_Regime | 89,259.80 | -10.74 | 41 | 24.08 | 107,248.50 |
| holdout_2026_cost_stress | TCELL | Adaptive_Regime | 99,888.73 | -0.11 | 18 | 16.60 | 102,369.59 |
| development_2025 | TCELL | SMA_Crossover | 94,173.28 | -5.83 | 7 | 9.75 | 103,900.50 |
| holdout_2026 | TCELL | SMA_Crossover | 99,565.73 | -0.43 | 4 | 5.98 | 102,779.40 |
| holdout_2026_H1 | TCELL | SMA_Crossover | 102,642.58 | 2.64 | 3 | 3.08 | 114,859.10 |
| holdout_2026_H2 | TCELL | SMA_Crossover | 97,002.64 | -3.00 | 1 | 3.00 | 89,479.70 |
| full_retrospective | TCELL | SMA_Crossover | 93,759.19 | -6.24 | 11 | 9.75 | 107,248.50 |
| holdout_2026_cost_stress | TCELL | SMA_Crossover | 98,083.10 | -1.92 | 4 | 7.20 | 102,369.59 |
| development_2025 | FROTO | Adaptive_Regime | 109,000.85 | 9.00 | 20 | 12.29 | 106,670.58 |
| holdout_2026 | FROTO | Adaptive_Regime | 105,577.46 | 5.58 | 24 | 24.53 | 81,894.33 |
| holdout_2026_H1 | FROTO | Adaptive_Regime | 102,690.56 | 2.69 | 13 | 24.53 | 94,137.33 |
| holdout_2026_H2 | FROTO | Adaptive_Regime | 102,811.41 | 2.81 | 11 | 2.37 | 86,998.00 |
| full_retrospective | FROTO | Adaptive_Regime | 115,063.61 | 15.06 | 44 | 24.54 | 87,599.95 |
| holdout_2026_cost_stress | FROTO | Adaptive_Regime | 95,915.27 | -4.08 | 24 | 27.81 | 81,563.85 |
| development_2025 | FROTO | SMA_Crossover | 109,588.92 | 9.59 | 2 | 2.41 | 106,670.58 |
| holdout_2026 | FROTO | SMA_Crossover | 97,001.21 | -3.00 | 1 | 3.00 | 81,894.33 |
| holdout_2026_H1 | FROTO | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 94,137.33 |
| holdout_2026_H2 | FROTO | SMA_Crossover | 97,001.21 | -3.00 | 1 | 3.00 | 86,998.00 |
| full_retrospective | FROTO | SMA_Crossover | 106,303.01 | 6.30 | 3 | 5.34 | 87,599.95 |
| holdout_2026_cost_stress | FROTO | SMA_Crossover | 96,709.53 | -3.29 | 1 | 3.29 | 81,563.85 |
| development_2025 | EREGL | Adaptive_Regime | 97,494.68 | -2.51 | 19 | 23.91 | 98,143.55 |
| holdout_2026 | EREGL | Adaptive_Regime | 139,871.42 | 39.87 | 10 | 15.65 | 152,542.16 |
| holdout_2026_H1 | EREGL | Adaptive_Regime | 140,165.37 | 40.17 | 6 | 15.65 | 171,809.93 |
| holdout_2026_H2 | EREGL | Adaptive_Regime | 99,890.49 | -0.11 | 5 | 12.49 | 88,876.00 |
| full_retrospective | EREGL | Adaptive_Regime | 136,375.41 | 36.38 | 29 | 23.91 | 150,091.04 |
| holdout_2026_cost_stress | EREGL | Adaptive_Regime | 134,395.05 | 34.40 | 10 | 16.32 | 151,939.09 |
| development_2025 | EREGL | SMA_Crossover | 96,997.28 | -3.00 | 2 | 3.00 | 98,143.55 |
| holdout_2026 | EREGL | SMA_Crossover | 99,681.95 | -0.32 | 2 | 5.34 | 152,542.16 |
| holdout_2026_H1 | EREGL | SMA_Crossover | 99,681.95 | -0.32 | 2 | 5.34 | 171,809.93 |
| holdout_2026_H2 | EREGL | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 88,876.00 |
| full_retrospective | EREGL | SMA_Crossover | 96,689.07 | -3.31 | 4 | 5.34 | 150,091.04 |
| holdout_2026_cost_stress | EREGL | SMA_Crossover | 98,986.38 | -1.01 | 2 | 5.81 | 151,939.09 |

Yerel verinin kaynağı bağımsız doğrulanmamıştır. Gerçek tarih kapsamı ve dosya SHA-256 değerleri `manifest.json` içindedir. 1 Ekim verisi eksikse challenge teslimi tam dönem olarak onaylanamaz.
