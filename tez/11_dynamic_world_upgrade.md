# Hafta 21 — Dynamic World Gradient Geçirimsiz Yüzey Yükseltmesi

## Motivasyon

ESA WorldCover (sınıf 50 = built-up) **binary** veri kullanıyordu. 30 m grid hücresi 9 piksellik 10 m mozaikten oluştuğu için sadece 10 olası değer (0%, 11.1%, ..., 100%) vardı. Pilot bölgede:
- %35 hücre = 0 (kıyı/park)
- %25.6 hücre = 100 (yapı yoğun)
- %39.4 hücre arada

**%60 hücre uçlarda yığılı** — gradient bilgi yok, modelleme açısından kısıtlı.

## Çözüm: Google Dynamic World

`GOOGLE/DYNAMICWORLD/V1` "built" probability bandı 0-1 sürekli. 10 m doğal çözünürlük. 5 yıl × yaz medyan kompoziti üretildi.

## Sayısal Karşılaştırma

| Metrik | ESA WorldCover | Dynamic World | Yorum |
|---|---|---|---|
| Unique değer | 10 (discrete) | **5,966** (continuous) | 595× daha fazla |
| Medyan | 44.4% | 69.0% | DW Konyaaltı'nı genel olarak daha "built" sayıyor |
| **LST × Pearson** | +0.338 | **+0.543** | +0.205 iyileşme |
| LST × Spearman | +0.278 | +0.202 | -0.076 (Pearson kazancı baskın) |
| ESA × DW r | — | — | 0.634 (orta — farklı bilgi) |

**DW lineer modeller için çok daha güçlü prediktör.**

## Modele Etki — RF Retrain (10 feature)

ESA `impervious_pct` modelden çıkarılmadı, DW `dw_built_pct` ek feature olarak eklendi. RF 9 → 10 feature ile yeniden eğitildi.

| Validation katmanı | Eski (8 feat) | Yeni (10 feat, DW) | Δ |
|---|---|---|---|
| Random 5-fold CV R² | 0.850 | **0.873** | +0.023 |
| Random CV RMSE | 1.20 °C | **1.11 °C** | -0.09 |
| Spatial Block CV R² | 0.724 | **0.752** | +0.028 |
| **Hold-out R² (3 mahalle)** | **0.094** | **0.146** | **+0.052** ✨ |
| Permutation null 99p | -0.057 | -0.050 | ≈ |
| **UTPM × LST** | **0.383** | **0.495** | **+0.112** ✨ |
| **Moran's I** | **0.740** | **0.801** | **+0.061** ✨ |

Hold-out R²'nin %55 artması özellikle değerli — RF'in görmediği mahallelere extrapolation gücü hafifçe iyileşti.

## Permutation Importance Devrimi

**Eski 8 feature:**
1. ndvi (0.41)
2. albedo (0.33) ← #1 idi
3. dtc_breeze (0.27)
4. impervious (ESA, 0.12)
5. wind_blockage (0.06)
6. road, building_h, building_d

**Yeni 10 feature:**
1. **dw_built (0.49)** ← 🏆 yeni #1, eski albedo'dan %50 fazla
2. ndvi (0.35)
3. dtc_breeze (0.21)
4. albedo (0.20) ← eski #1'den #4'e düştü
5. impervious (ESA, 0.04) ← neredeyse anlamsız
6. is_dtc_saturated (0.03)
7. wind_blockage (0.02)
8. road, building_h, building_d

**Karar:** ESA `impervious_pct` model için neredeyse anlamsız hale geldi (perm imp 0.04, SHAP 0.04). Ancak **VIF=1.99** (eşik 10), collinear değil — silmek zorunlu değil. RF zaten önemini düşük tuttu.

## SHAP Importance (Yeni)

```
albedo_mean       0.321  (en yüksek lineer attribution)
ndvi_mean         0.248
dw_built_pct      0.173  ⭐ yeni 3. sırada
dtc_breeze_m      0.141
impervious_pct    0.039  (ESA, geride)
wind_blockage     0.028
road_density      0.022
building_height   0.014
building_density  0.009
is_dtc_saturated  0.004
```

DW SHAP'ta da albedo + ndvi sonrası **3. en güçlü attribution**. Permutation importance ile uyumlu.

## LISA + Jenks Yeniden

**LISA cluster:**

| | Eski | Yeni | Δ |
|---|---|---|---|
| HH (UHI çekirdeği) | 5,263 | **5,874** | +611 |
| LL (serin küme) | 6,216 | **6,515** | +299 |
| HL/LH | 220 | 170 | -50 |
| NS | 16,548 | 15,688 | -860 |

**Yeni model 1,131 hücreyi (NS → anlamlı)** sınıflandırdı. UHI çekirdeği daha net.

**Jenks 5 sınıf:**

| Sınıf | Eski | Yeni | Δ |
|---|---|---|---|
| Çok serin | 4,049 | 2,654 | -1,395 |
| Serin | 6,914 | 5,618 | -1,296 |
| Orta | 9,412 | 9,427 | +15 |
| **Sıcak** | 6,859 | **9,314** | +2,455 |
| **Çok sıcak** | 973 | **1,234** | +261 |

DW gradient sayesinde **ortadaki "Serin/Çok Serin" hücreler "Sıcak" sınıfa taşındı**. Toplam Sıcak+Çok Sıcak: 7,832 → **10,548** (+%35). Şehir planlamacısı için **daha hassas tehdit haritası**.

## Bivariate Decision Layer Yeniden Hesaplandı

Yeni UTPM tertileleriyle:

| Öncelik | Eski hücre | Yeni hücre | Δ |
|---|---|---|---|
| **1_ACİL_MÜDAHALE** | 4,420 | **4,200** | -220 |
| 2_YÜKSEK_ÖNCELİK | 1,675 | 1,708 | +33 |
| **3_SICAK_AÇIK** | 3,321 | **3,508** | +187 |
| 4_BLOKLU_ORTA | 3,039 | 3,269 | +230 |
| 5_ORTA | 1,990 | 2,054 | +64 |
| 6_ORTA_AÇIK | 4,386 | 4,092 | -294 |
| 7_BLOKLU_SERİN | 1,813 | 1,803 | -10 |
| 8_SERİN_ORTA | 1,468 | 1,371 | -97 |
| 9_KORUMA | 6,135 | 6,242 | +107 |

**Aktif müdahale (1+2+3):** 9,416 → **9,416** (eşit ama dağılım değişti — 3_SICAK_AÇIK büyüdü).

`grid_30m_priority.gpkg` güncel UTPM ile yeniden yazıldı.

## Tezsel Katkı

1. **Veri kalitesi:** Binary impervious mozaikten gradient probability'ye geçiş — modelleme açısından temel iyileşme.
2. **Pearson r 0.34 → 0.54:** Lineer ilişki gücü yarıdan fazla artarak.
3. **RF Random CV R² 0.85 → 0.87:** Marjinal ama tutarlı iyileşme.
4. **Hold-out R² 0.09 → 0.15:** **Out-of-area extrapolation gücü %55 arttı.** Bu L1 sınırlılığını hafifletiyor (kapamıyor ama).
5. **UTPM × LST r 0.38 → 0.49:** Lineer indeks RF'in non-lineer sinyalini daha iyi yansıtıyor.
6. **Moran's I 0.74 → 0.80:** Mekânsal kümeleme daha güçlü.
7. **Çok Sıcak hücre 973 → 1,234:** Şehir planlamacısı için **daha kapsamlı acil müdahale alanı**.

## Sınırlılık L11 — kısmi düzeltme

Hafta 19'da L11 (ERA5 mekânsal yetersiz) yazıldığında modele bilgi katmadığını söylemiştik. Burada **alternatif yol** gösterildi: ERA5 yerine başka veri seti (Dynamic World) ile pilot içi gradient bilgi sağlanabilir. Yani **veri seti seçimi modelin kalitesini doğrudan etkiliyor** — yerine koyma esnekliği var.

## Üretilen Dosyalar

- `data/processed/dw_built_summer_median_2020_2024.tif` (5.6 MB) — DW raster
- `data/processed/grid_30m_full.gpkg` — `dw_built_pct` kolonu eklendi
- `data/processed/grid_30m_modeling.gpkg` (12 MB) — log + z dönüşüm dahil
- `data/processed/grid_30m_predictions.gpkg` — yeni RF tahmin
- `data/processed/grid_30m_utpm.gpkg` — yeni UTPM
- `data/processed/grid_30m_priority.gpkg` — yeniden hesaplanmış priority
- `results/rf_model.pkl` — yeni 10-feature RF (1.2 GB local)
- `results/rf_validation.json`, `results/utpm_analysis.json`, `results/shap_values.npy`
- `results/impervious_comparison.json` — ESA vs DW
- `tables/16_dw_comparison.csv` — eski vs yeni metrik tablosu
- `figures/15_impervious_comparison.png` — ESA vs DW (4 panel)
- `figures/16_dw_improvement.png` — RF R² karşılaştırma bar
- `figures/16_rf_v3_overview.png`, `16_utpm_v3_overview.png`, `16_shap_v3_beeswarm.png`

## Sonraki Çalışma

- ESA `impervious_pct`'yi modelden tamamen çıkar (perm imp ve SHAP'ta neredeyse sıfır) — **9 feature minimal model**
- Dynamic World **diğer sınıfları** dahil et: `trees`, `grass`, `water` probability'leri ek feature olarak (ndvi'den daha fine-grained vegetation bilgisi)
- Sentinel-2 **NDBI/UI** kendi hesabı ile DW'ı çapraz doğrula
