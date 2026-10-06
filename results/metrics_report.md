# BIST Algorithmic Trading Challenge - Performans Raporu
**Strateji:** Adaptive_Regime  
**Genel Durum:** ⚠️ **FAILED** (3/6 hisse basarili)  
**Toplam Portfoy:** 600,000 TL -> 913,200 TL (+313,200 TL | +52.20%)  

## Hisse Bazli Benchmark Karsilastirmasi

| Hisse | Baslangic | Final | Net Kar | Benchmark | Fark | Trades | Win% | MaxDD% | Durum |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AKBNK** | 100,000 TL | 79,819 TL | -20,181 TL | 184,000 TL | -104,181 TL | 10 | %40.0 | -%50.7 | FAIL |
| **ASELS** | 100,000 TL | 240,922 TL | +140,922 TL | 339,000 TL | -98,078 TL | 8 | %75.0 | -%25.0 | FAIL |
| **TUPRS** | 100,000 TL | 200,750 TL | +100,750 TL | 172,000 TL | +28,750 TL | 7 | %85.7 | -%17.9 | PASS |
| **TCELL** | 100,000 TL | 111,925 TL | +11,925 TL | 82,000 TL | +29,925 TL | 14 | %57.1 | -%29.5 | PASS |
| **FROTO** | 100,000 TL | 101,934 TL | +1,934 TL | 103,000 TL | -1,066 TL | 15 | %66.7 | -%38.6 | FAIL |
| **EREGL** | 100,000 TL | 177,850 TL | +77,850 TL | 139,000 TL | +38,850 TL | 11 | %81.8 | -%19.5 | PASS |

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

- Parametreler: `{'fast_period': 20, 'slow_period': 60, 'rsi_period': 3, 'mean_period': 10, 'atr_period': 14, 'warmup_period': 60, 'oversold': 20.0, 'pullback': 50.0, 'overbought': 70.0, 'atr_multiplier': 5.0}`
- Emir modu: `next_open`
- Komisyon: 0.0; kayma: 0.0
- Harici risk yoneticisi: `None`
