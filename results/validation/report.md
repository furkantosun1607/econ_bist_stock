# Kronolojik strateji doğrulaması

Strateji: **Adaptive_Regime**. Parametreler: `{'fast_period': 20, 'slow_period': 60, 'rsi_period': 3, 'mean_period': 10, 'atr_period': 14, 'warmup_period': 60, 'oversold': 20.0, 'pullback': 50.0, 'overbought': 70.0, 'atr_multiplier': 5.0}`.

2025 geliştirme dönemidir. 2026 ayrı tarihsel değerlendirmedir. Tam dönem sonucu bağımsız ileri test sayılmaz. Her alt dönemde hesap 100.000 TL ile yeniden başlar; göstergeler geçmiş veriyi korur. Önceki kapanış sinyali ilk açılışta uygulanabilir. Son kapanışta açık pozisyon tasfiye edilir.

Maliyet stresi: her yönde %0,10 komisyon + %0,10 kayma. Al-tut aynı maliyetleri içerir. Benchmark hedefleri tam dönem içindir; alt dönemlere PASS/FAIL uygulanmaz.

| Dönem | Hisse | Strateji | Final TL | Getiri % | İşlem | Max DD % | Al-tut TL |
|---|---|---|---:|---:|---:|---:|---:|
| development_2025 | AKBNK | Adaptive_Regime | 118,270.44 | 18.27 | 5 | 18.59 | 109,025.23 |
| holdout_2026 | AKBNK | Adaptive_Regime | 67,205.82 | -32.79 | 6 | 50.67 | 98,641.29 |
| holdout_2026_H1 | AKBNK | Adaptive_Regime | 79,842.41 | -20.16 | 4 | 39.78 | 113,361.29 |
| holdout_2026_H2 | AKBNK | Adaptive_Regime | 84,493.41 | -15.51 | 3 | 19.09 | 87,360.90 |
| full_retrospective | AKBNK | Adaptive_Regime | 79,818.61 | -20.18 | 10 | 50.68 | 108,005.86 |
| holdout_2026_cost_stress | AKBNK | Adaptive_Regime | 65,604.10 | -34.40 | 6 | 51.66 | 98,247.65 |
| development_2025 | AKBNK | SMA_Crossover | 110,871.78 | 10.87 | 2 | 5.37 | 109,025.23 |
| holdout_2026 | AKBNK | SMA_Crossover | 92,345.80 | -7.65 | 3 | 7.65 | 98,641.29 |
| holdout_2026_H1 | AKBNK | SMA_Crossover | 95,065.30 | -4.93 | 2 | 4.93 | 113,361.29 |
| holdout_2026_H2 | AKBNK | SMA_Crossover | 97,139.80 | -2.86 | 1 | 2.86 | 87,360.90 |
| full_retrospective | AKBNK | SMA_Crossover | 102,388.55 | 2.39 | 5 | 9.38 | 108,005.86 |
| holdout_2026_cost_stress | AKBNK | SMA_Crossover | 91,204.26 | -8.80 | 3 | 8.80 | 98,247.65 |
| development_2025 | ASELS | Adaptive_Regime | 171,596.82 | 71.60 | 5 | 18.87 | 317,932.36 |
| holdout_2026 | ASELS | Adaptive_Regime | 140,265.00 | 40.27 | 4 | 25.02 | 145,039.50 |
| holdout_2026_H1 | ASELS | Adaptive_Regime | 148,703.00 | 48.70 | 1 | 20.51 | 148,703.00 |
| holdout_2026_H2 | ASELS | Adaptive_Regime | 94,304.00 | -5.70 | 4 | 16.70 | 97,543.50 |
| full_retrospective | ASELS | Adaptive_Regime | 240,922.33 | 140.92 | 8 | 25.02 | 461,717.97 |
| holdout_2026_cost_stress | ASELS | Adaptive_Regime | 138,054.27 | 38.05 | 4 | 26.04 | 144,446.13 |
| development_2025 | ASELS | SMA_Crossover | 97,184.37 | -2.82 | 1 | 2.82 | 317,932.36 |
| holdout_2026 | ASELS | SMA_Crossover | 104,506.40 | 4.51 | 1 | 1.37 | 145,039.50 |
| holdout_2026_H1 | ASELS | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 148,703.00 |
| holdout_2026_H2 | ASELS | SMA_Crossover | 104,506.40 | 4.51 | 1 | 1.37 | 97,543.50 |
| full_retrospective | ASELS | SMA_Crossover | 101,570.37 | 1.57 | 2 | 2.82 | 461,717.97 |
| holdout_2026_cost_stress | ASELS | SMA_Crossover | 104,098.63 | 4.10 | 1 | 1.57 | 144,446.13 |
| development_2025 | TUPRS | Adaptive_Regime | 145,699.46 | 45.70 | 4 | 12.13 | 142,429.06 |
| holdout_2026 | TUPRS | Adaptive_Regime | 137,798.53 | 37.80 | 3 | 17.56 | 216,027.22 |
| holdout_2026_H1 | TUPRS | Adaptive_Regime | 107,059.15 | 7.06 | 2 | 17.56 | 128,345.82 |
| holdout_2026_H2 | TUPRS | Adaptive_Regime | 128,723.67 | 28.72 | 1 | 8.21 | 168,281.50 |
| full_retrospective | TUPRS | Adaptive_Regime | 200,750.16 | 100.75 | 7 | 17.86 | 307,855.17 |
| holdout_2026_cost_stress | TUPRS | Adaptive_Regime | 136,124.63 | 36.12 | 3 | 17.89 | 215,194.49 |
| development_2025 | TUPRS | SMA_Crossover | 90,435.45 | -9.56 | 3 | 9.77 | 142,429.06 |
| holdout_2026 | TUPRS | SMA_Crossover | 117,443.55 | 17.44 | 2 | 3.28 | 216,027.22 |
| holdout_2026_H1 | TUPRS | SMA_Crossover | 102,677.44 | 2.68 | 1 | 2.11 | 128,345.82 |
| holdout_2026_H2 | TUPRS | SMA_Crossover | 114,381.58 | 14.38 | 1 | 1.22 | 168,281.50 |
| full_retrospective | TUPRS | SMA_Crossover | 106,241.69 | 6.24 | 5 | 9.77 | 307,855.17 |
| holdout_2026_cost_stress | TUPRS | SMA_Crossover | 116,520.47 | 16.52 | 2 | 3.66 | 215,194.49 |
| development_2025 | TCELL | Adaptive_Regime | 100,492.04 | 0.49 | 8 | 17.49 | 103,900.50 |
| holdout_2026 | TCELL | Adaptive_Regime | 110,900.35 | 10.90 | 7 | 29.48 | 102,779.40 |
| holdout_2026_H1 | TCELL | Adaptive_Regime | 99,526.81 | -0.47 | 4 | 28.42 | 114,859.10 |
| holdout_2026_H2 | TCELL | Adaptive_Regime | 111,427.29 | 11.43 | 4 | 4.81 | 89,479.70 |
| full_retrospective | TCELL | Adaptive_Regime | 111,925.09 | 11.93 | 14 | 29.48 | 107,248.50 |
| holdout_2026_cost_stress | TCELL | Adaptive_Regime | 107,840.11 | 7.84 | 7 | 30.60 | 102,369.59 |
| development_2025 | TCELL | SMA_Crossover | 94,173.28 | -5.83 | 7 | 9.75 | 103,900.50 |
| holdout_2026 | TCELL | SMA_Crossover | 99,565.73 | -0.43 | 4 | 5.98 | 102,779.40 |
| holdout_2026_H1 | TCELL | SMA_Crossover | 102,642.58 | 2.64 | 3 | 3.08 | 114,859.10 |
| holdout_2026_H2 | TCELL | SMA_Crossover | 97,002.64 | -3.00 | 1 | 3.00 | 89,479.70 |
| full_retrospective | TCELL | SMA_Crossover | 93,759.19 | -6.24 | 11 | 9.75 | 107,248.50 |
| holdout_2026_cost_stress | TCELL | SMA_Crossover | 98,083.10 | -1.92 | 4 | 7.20 | 102,369.59 |
| development_2025 | FROTO | Adaptive_Regime | 100,351.84 | 0.35 | 8 | 21.03 | 106,670.58 |
| holdout_2026 | FROTO | Adaptive_Regime | 101,300.06 | 1.30 | 8 | 38.58 | 81,894.33 |
| holdout_2026_H1 | FROTO | Adaptive_Regime | 92,895.64 | -7.10 | 4 | 35.73 | 94,137.33 |
| holdout_2026_H2 | FROTO | Adaptive_Regime | 109,048.06 | 9.05 | 5 | 5.16 | 86,998.00 |
| full_retrospective | FROTO | Adaptive_Regime | 101,934.34 | 1.93 | 15 | 38.58 | 87,599.95 |
| holdout_2026_cost_stress | FROTO | Adaptive_Regime | 98,123.43 | -1.88 | 8 | 39.52 | 81,563.85 |
| development_2025 | FROTO | SMA_Crossover | 109,588.92 | 9.59 | 2 | 2.41 | 106,670.58 |
| holdout_2026 | FROTO | SMA_Crossover | 97,001.21 | -3.00 | 1 | 3.00 | 81,894.33 |
| holdout_2026_H1 | FROTO | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 94,137.33 |
| holdout_2026_H2 | FROTO | SMA_Crossover | 97,001.21 | -3.00 | 1 | 3.00 | 86,998.00 |
| full_retrospective | FROTO | SMA_Crossover | 106,303.01 | 6.30 | 3 | 5.34 | 87,599.95 |
| holdout_2026_cost_stress | FROTO | SMA_Crossover | 96,709.53 | -3.29 | 1 | 3.29 | 81,563.85 |
| development_2025 | EREGL | Adaptive_Regime | 122,866.07 | 22.87 | 7 | 18.81 | 98,143.55 |
| holdout_2026 | EREGL | Adaptive_Regime | 144,386.13 | 44.39 | 5 | 18.15 | 152,542.16 |
| holdout_2026_H1 | EREGL | Adaptive_Regime | 135,896.76 | 35.90 | 3 | 18.15 | 171,809.93 |
| holdout_2026_H2 | EREGL | Adaptive_Regime | 106,355.05 | 6.36 | 3 | 16.60 | 88,876.00 |
| full_retrospective | EREGL | Adaptive_Regime | 177,849.68 | 77.85 | 11 | 19.53 | 150,091.04 |
| holdout_2026_cost_stress | EREGL | Adaptive_Regime | 141,522.89 | 41.52 | 5 | 18.47 | 151,939.09 |
| development_2025 | EREGL | SMA_Crossover | 96,997.28 | -3.00 | 2 | 3.00 | 98,143.55 |
| holdout_2026 | EREGL | SMA_Crossover | 99,681.95 | -0.32 | 2 | 5.34 | 152,542.16 |
| holdout_2026_H1 | EREGL | SMA_Crossover | 99,681.95 | -0.32 | 2 | 5.34 | 171,809.93 |
| holdout_2026_H2 | EREGL | SMA_Crossover | 100,000.00 | 0.00 | 0 | 0.00 | 88,876.00 |
| full_retrospective | EREGL | SMA_Crossover | 96,689.07 | -3.31 | 4 | 5.34 | 150,091.04 |
| holdout_2026_cost_stress | EREGL | SMA_Crossover | 98,986.38 | -1.01 | 2 | 5.81 | 151,939.09 |

Yerel verinin kaynağı bağımsız doğrulanmamıştır. Gerçek tarih kapsamı ve dosya SHA-256 değerleri `manifest.json` içindedir. 1 Ekim verisi eksikse challenge teslimi tam dönem olarak onaylanamaz.
