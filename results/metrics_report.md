# BIST Algorithmic Trading Challenge - Performans Raporu
**Strateji:** Adaptive_Regime  
**Genel Durum:** ⚠️ **FAILED** (5/6 hisse basarili)  
**Toplam Portfoy:** 600,000 TL -> 1,030,925 TL (+430,925 TL | +71.82%)  

## Hisse Bazli Benchmark Karsilastirmasi

| Hisse | Baslangic | Final | Net Kar | Benchmark | Fark | Trades | Win% | MaxDD% | Durum |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | 129,290 TL | +29,290 TL | 184,000 TL | -54,710 TL | 38 | %44.7 | -%16.9 | FAIL |
| **ASELS** | 100,000 TL | 349,082 TL | +249,082 TL | 339,000 TL | +10,082 TL | 23 | %65.2 | -%19.0 | PASS |
| **TUPRS** | 100,000 TL | 205,828 TL | +105,828 TL | 172,000 TL | +33,828 TL | 24 | %50.0 | -%14.6 | PASS |
| **TCELL** | 100,000 TL | 82,618 TL | -17,382 TL | 82,000 TL | +618 TL | 42 | %40.5 | -%29.6 | PASS |
| **FROTO** | 100,000 TL | 121,057 TL | +21,057 TL | 103,000 TL | +18,057 TL | 46 | %47.8 | -%18.8 | PASS |
| **EREGL** | 100,000 TL | 143,049 TL | +43,049 TL | 139,000 TL | +4,049 TL | 29 | %34.5 | -%23.9 | PASS |

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

- Parametreler: `{'fast_period': 15, 'slow_period': 50, 'rsi_period': 3, 'mean_period': 10, 'atr_period': 14, 'warmup_period': 50, 'cooldown_bars': 1, 'oversold': 20.0, 'pullback': 53.0, 'overbought': 70.0, 'atr_multiplier': 3.5, 'profit_atr_multiplier': 2.3, 'profit_threshold': 0.2, 'stop_loss_pct': 0.07, 'exit_on_slow_break': True}`
- Emir modu: `next_open`
- Komisyon: 0.0; kayma: 0.0
- Harici risk yoneticisi: `None`
