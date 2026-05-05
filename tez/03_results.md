# Sonuçlar — Sayısal Master Tablo

## A. Veri kapsamı

| Metrik | Değer |
|---|---|
| Pilot alan | 25.4 km² (MultiPolygon, 15 mahalle) |
| Toplam imar noktası | 43,423 (43,423 / Konyaaltı genel) |
| Pilot içi nokta | 18,575 |
| Kat verili (measured) | 12,788 |
| Kat eksik (imputed) | 5,787 (%31) |
| 30 m grid hücresi | **28,247** |
| 100 m grid hücresi | 2,906 |
| 30m / 100m hücre oranı | 9.72 |

## B. LST (Hedef değişken)

| Metrik | Değer |
|---|---|
| Yıl aralığı | 2020-2024 |
| Aylar | Haziran, Temmuz, Ağustos |
| Bulut eşiği | %10 |
| Toplam Landsat sahnesi | 71 |
| Kapsama | 100% (28,247/28,247) |
| **Min LST** | 29.78 °C |
| **Max LST** | 51.43 °C |
| **Medyan** | 43.16 °C |
| **Mean** | 42.54 °C |

## C. Bağımsız değişkenler — özet

| Değişken | Min | Medyan | Max | Mean | Std |
|---|---|---|---|---|---|
| ndvi_mean | -0.604 | 0.225 | 0.994 | 0.271 | 0.223 |
| albedo_mean | 0.020 | 0.207 | 0.717 | 0.209 | 0.071 |
| impervious_pct | 0.000 | 44.44 | 100.00 | 47.80 | 42.23 |
| building_height_mean (m, NaN→0) | 0 | 12.00* | 36.00 | — | — |
| building_density_per_km2 | 0 | 0 | 203,333 | — | — |
| road_density_m_per_km2 | 0 | 0** | 244,900 | — | — |
| dtc_breeze_m | 0.23 | 1,777 | 20,000 | — | — |

\* Sadece bina olan hücrelerde medyan 12.0 m  
\*\* Yol olmayan hücreler dahil — sadece yollu hücrelerde medyan farklıdır

## D. Korelasyonlar — Pearson, Spearman, SHAP karşılaştırma

| Değişken | Pearson r (raw) | Pearson r (z) | Spearman r | SHAP global |
|---|---|---|---|---|
| albedo_mean | +0.592 | +0.592 | +0.413 | **0.367** |
| **ndvi_mean** | +0.050 | +0.050 | **-0.251** | **0.267** |
| dtc_breeze_m | -0.654 | -0.174 | +0.018 | 0.182 |
| impervious_pct | +0.338 | +0.338 | +0.278 | 0.095 |
| road_density | +0.170 | +0.198 | +0.125 | 0.040 |
| building_height | -0.133 | -0.133 | -0.152 | 0.026 |
| building_density | +0.050 | +0.103 | +0.051 | 0.014 |

**Yorum:**
- DTC_breeze raw Pearson r=-0.654 ama Spearman ~0 → 1066 saturated outlier sürüklüyor
- NDVI Pearson zayıf (r=0.05) ama SHAP %27 → non-lineer ilişki
- Albedo en güçlü tek prediktör

## E. VIF — Multicollinearity yok

| Değişken | VIF |
|---|---|
| impervious_pct_z | 1.78 |
| albedo_mean_z | 1.43 |
| ndvi_mean_z | 1.26 |
| road_density_z | 1.19 |
| dtc_breeze_m_z | 1.12 |
| building_density_z | 1.06 |
| building_height_z | 1.03 |

**Eşik = 10. Hepsi 1.0-1.8 arasında → 7 değişkenin hepsi modele alındı.**

## F. Random Forest — 4 validation katmanı

| Katman | RMSE (°C) | MAE (°C) | R² | Yorum |
|---|---|---|---|---|
| **Random 5-fold CV** | **1.221** | 0.922 | **0.846** | İn-distribution güçlü |
| Spatial Block CV (500m) | 1.418 | 1.081 | 0.720 | Autocorrelation gap 0.13 |
| Mahalle hold-out (3) | 1.436 | 1.129 | **0.105** | Out-of-area zayıf |
| Permutation null R² 99p | — | — | -0.061 | Gerçek model anlamlı (p<0.01) |

**Saturated DTC hücreler için RMSE:** ayrı raporlanır (sınırlılık).

## G. Yıllar arası validation

| Yıl | n | Actual mean (°C) | RMSE | MAE | R² |
|---|---|---|---|---|---|
| 2020 | 28,247 | 40.78 | 2.116 | 1.818 | 0.505 |
| 2021 | 28,247 | 41.73 | 1.238 | 1.052 | **0.859** |
| 2022 | 28,247 | **44.69** | 2.886 | 2.282 | 0.491 |
| 2023 | 28,247 | 42.60 | 0.598 | 0.454 | **0.964** |
| 2024 | 28,247 | 42.39 | 0.612 | 0.481 | **0.961** |

**Yıllar arası LST korelasyonu:**

|  | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 2020 | 1.000 | 0.884 | 0.797 | 0.927 | 0.927 |
| 2021 | 0.884 | 1.000 | 0.888 | 0.955 | 0.955 |
| 2022 | 0.797 | 0.888 | 1.000 | 0.868 | 0.869 |
| 2023 | 0.927 | 0.955 | 0.868 | 1.000 | **0.983** |
| 2024 | 0.927 | 0.955 | 0.869 | 0.983 | 1.000 |

**Diagonal-dışı korelasyon: min=0.797, mean=0.905, max=0.983** → mekânsal LST deseni yıllar arası **çok tutarlı**.

## H. Persistence (Hafta 11)

| Persistence kategorisi | Hücre |
|---|---|
| **Persistent HOT** (5/5 yıl Q4) | **2,008** |
| 4/5 yıl Q4 | yüksek sayıda (detay JSON'da) |
| Hiç Q4 olmayan | 14,653 |
| **Persistent COLD** (5/5 yıl Q1) | **3,390** |
| Yıllık LST std medyanı | 1.50 °C |

## I. SHAP + UTPM (Hafta 12-13)

**SHAP global importance** (1000 sample, approximate):

```
albedo            0.367
ndvi              0.267
dtc_breeze        0.182
impervious        0.095
road_density      0.040
building_height   0.026
building_density  0.014
is_dtc_saturated  0.009
```

**UTPM lineer indeks (0-100):**
- min 0.0 / med 37.2 / max 100.0
- UTPM × LST (5-yıl medyan) r = **0.371**
- UTPM × Persistence (Q4 yıl sayısı) r = **0.333**

## J. Mekânsal otokorelasyon

| Metrik | Değer |
|---|---|
| **Global Moran's I** | **0.7380** |
| Beklenen I | -0.0000 |
| z-score | **249.41** |
| p-value | < 0.0001 |
| Permütasyon p | < 0.01 |

**Sonuç:** UTPM mekânsal olarak güçlü kümeli (rastgele değil).

### LISA Local Moran cluster dağılımı

| Cluster | Hücre | % | Anlam |
|---|---|---|---|
| **HH** | **5,181** | **18.3** | UHI çekirdeği |
| **LL** | **5,860** | **20.7** | Serin küme (kıyı/park) |
| HL | 146 | 0.5 | Yerel sıcak anomali |
| LH | 141 | 0.5 | Yerel serin anomali |
| NS | 16,919 | 60.0 | İstatistiksel anlamlı küme yok |

## K. Jenks Natural Breaks — 5 sınıf karar destek

| Sınıf | UTPM aralığı | Hücre | % | Yorum |
|---|---|---|---|---|
| Çok serin | 0.0 – 21.3 | 4,049 | 14.3 | Plaj, park, kıyı |
| Serin | 21.3 – 33.6 | 6,888 | 24.4 | Düşük yapı, yeşil |
| Orta | 33.6 – 43.6 | 9,641 | 34.1 | Karışık doku |
| Sıcak | 43.6 – 58.6 | 6,788 | 24.0 | Yapı yoğun + asfalt |
| **Çok sıcak** | **58.6 – 100.0** | **881** | **3.1** | **Acil müdahale** |

**0.79 km² = pilotun %3.1'i şehir planlamacısının ilk hedef alanı.**

## L. Üretilen dosya boyutları (özet)

| Dosya | Boyut | İçerik |
|---|---|---|
| `grid_30m_full.gpkg` | 8.9 MB | 7 değişken + LST |
| `grid_30m_modeling.gpkg` | 10.3 MB | + log + z transformları |
| `grid_30m_predictions.gpkg` | 7.3 MB | RF tahmin + residual |
| `grid_30m_persistence.gpkg` | 7.3 MB | 5 yıl persistence |
| `grid_30m_utpm.gpkg` | **7.8 MB** | **Final ürün** |
| `rf_model.pkl` | **1.2 GB** | RF model (local-only) |
| 5 LST raster | ~2.5 MB | Yıllık LST |
| 4 diğer raster | ~12 MB | NDVI, Albedo, Impervious, GHSL |
