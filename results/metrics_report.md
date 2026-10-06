# BIST Algorithmic Trading Challenge - Performans Raporu
**Strateji:** Adaptive_Regime  
**Genel Durum:** ⚠️ **FAILED** (4/6 hisse basarili)  
**Toplam Portfoy:** 600,000 TL -> 1,012,139 TL (+412,139 TL | +68.69%)  

## Hisse Bazli Benchmark Karsilastirmasi

| Hisse | Baslangic | Final | Net Kar | Benchmark | Fark | Trades | Win% | MaxDD% | Durum |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | 129,290 TL | +29,290 TL | 184,000 TL | -54,710 TL | 38 | %44.7 | -%16.9 | FAIL |
| **ASELS** | 100,000 TL | 349,082 TL | +249,082 TL | 339,000 TL | +10,082 TL | 23 | %65.2 | -%19.0 | PASS |
| **TUPRS** | 100,000 TL | 193,067 TL | +93,067 TL | 172,000 TL | +21,067 TL | 23 | %52.2 | -%14.6 | PASS |
| **TCELL** | 100,000 TL | 89,260 TL | -10,740 TL | 82,000 TL | +7,260 TL | 41 | %41.5 | -%24.1 | PASS |
| **FROTO** | 100,000 TL | 115,064 TL | +15,064 TL | 103,000 TL | +12,064 TL | 44 | %47.7 | -%24.5 | PASS |
| **EREGL** | 100,000 TL | 136,375 TL | +36,375 TL | 139,000 TL | -2,625 TL | 29 | %34.5 | -%23.9 | FAIL |

## Challenge Kurali Hatirlatmasi
> [!IMPORTANT]
> Toplam portfoy kari tek basina yeterli degildir. 6 hissenin tamaminin bireysel benchmark hedefini gecmesi ve her birinde en az 3 tamamlanmis islem bulunmasi zorunludur.


## Veri Kapsami

- AKBNK: 2025-01-02 — 2026-09-30 (440 bar).
- ASELS: 2025-01-02 — 2026-09-30 (440 bar).
- TUPRS: 2025-01-02 — 2026-09-30 (440 bar).
- TCELL: 2025-01-02 — 2026-09-30 (440 bar).
- FROTO: 2025-01-02 — 2026-09-30 (440 bar).
- EREGL: 2025-01-02 — 2026-09-30 (440 bar).

**Gecici sonuc:** Istenen son tarih veride yok. Bu tablo mevcut orneklemin benchmark karsilastirmasidir; tam donem challenge basarisi olarak onaylanamaz.

## Calistirma Ayarlari

- Parametreler: `{'fast_period': 15, 'slow_period': 50, 'rsi_period': 3, 'mean_period': 10, 'atr_period': 14, 'warmup_period': 50, 'cooldown_bars': 1, 'oversold': 20.0, 'pullback': 50.0, 'overbought': 70.0, 'atr_multiplier': 3.5, 'profit_atr_multiplier': 2.3, 'profit_threshold': 0.2, 'stop_loss_pct': 0.08, 'exit_on_slow_break': True}`
- Emir modu: `next_open`
- Komisyon: 0.0; kayma: 0.0
- Harici risk yoneticisi: `None`
