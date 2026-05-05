# UTPM Konyaaltı — Proje Özeti & Görsel Kullanım Akışı

> Bu dosya iki bölümlüdür:
> 1. **Proje Özeti** — Sistemi en basit dilde madde madde anlatır
> 2. **Görsel Akışı** — 31 görselin hangi tez bölümünde nasıl kullanılacağı

---

# BÖLÜM 1 — PROJE ÖZETİ (En Basit Dil)

## Ne Yaptık?

1. **Antalya Konyaaltı'nda 15 mahalleli sahil koridorunu** (25.4 km², 28,247 küçük 30×30 m kare) inceledik.
2. Bu bölgenin **yaz öğle sıcaklığını** (LST = Land Surface Temperature) **uydu görüntülerinden** ölçtük (Landsat 8/9, 2020-2024 yaz medyan).
3. Her küçük karenin sıcak veya serin olmasının **sebeplerini** araştırdık. 7 farklı özelliği kullandık:
   - Yeşillik (NDVI) — Sentinel-2 uydusu
   - Yansıtıcılık (Albedo) — Sentinel-2 uydusu
   - Geçirimsiz yüzey % (Built-up) — Google Dynamic World
   - Bina yüksekliği — Konyaaltı imar verisi
   - Yol yoğunluğu — OpenStreetMap
   - Rüzgar yönelimli kıyı mesafesi (DTC_breeze) — OSM coastline + ışın hesabı
   - Rüzgar blokajı (Wind Blockage) — bina yüksekliklerinin ışın boyunca toplamı
4. **Random Forest makine öğrenmesi modeli** kurduk. Sıcaklık ile bu 7 özellik arasındaki ilişkiyi öğrendi.
5. Modelin **0-100 arası bir skor** üretmesini sağladık (UTPM skoru). Yüksek skor = sıcak hücre, düşük = serin.
6. **Şehir planlamacısı için 5 sınıflık karar haritası** ürettik (Çok serin / Serin / Orta / Sıcak / Çok sıcak).
7. Yüksek-Sıcak hücreleri rüzgar blokajı ile birleştirip **9 sınıflık eylem önceliği** sunduk (1_ACİL_MÜDAHALE → 9_KORUMA).
8. Modeli **5 yıl boyunca** test ettik (her yıl ayrı). Aynı yerler **kalıcı sıcak** çıktı.
9. **Streamlit web uygulaması** yaptık — kullanıcı haritaya tıklar, AI yorumu (Claude API) alır.
10. Modeli **akademik standartta doğruladık**: 5 baseline model karşılaştırma, bootstrap CI95, hyperparameter tuning, parsimony test, MODIS uydu çapraz doğrulama, residual diagnostic.

## Ana Sonuçlar (En Basit Anlam)

11. **Random Forest modelimiz LST'yi %87 doğrulukla tahmin ediyor** (R² = 0.870, RMSE 1.12°C). Lineer modeller ancak %67 → demek ki ilişkiler doğrusal değil.
12. **2,008 hücre 5 yıl boyunca en sıcak %25 dilimde** kaldı = **kalıcı kentsel ısı çekirdeği**. Bu UTPM hipotezimizi doğruluyor.
13. **881 hücre "Çok sıcak" sınıfta** (0.79 km²). Şehir planlamacısının **acil müdahale alanı**.
14. **Mekânsal kümeleme istatistiksel** olarak güçlü (Moran's I = 0.738, p<0.001). UHI rastgele değil, fizksel.
15. **En önemli prediktörler:**
    - **Albedo** (Akdeniz beton/kireç çatı bulgusu)
    - **NDVI** (yeşillik — non-lineer ilişki, RF yakaladı)
    - **Dynamic World built %** (gradient yapılaşma yoğunluğu)
    - **DTC_breeze** (rüzgar yönelimli kıyı mesafesi)

## Tezsel Önemli Bulgular

16. **Out-of-time validation R² = 0.917** — model 2020-2023 verisinden 2024'ü mükemmel tahmin etti. Temporal generalization güçlü.
17. **Albedo × LST korelasyonu pozitif (+0.59)** — geleneksel UHI literatüründe negatif beklenir; Akdeniz beton yapısı için Bonafoni-Sekertekin (2020) ile uyumlu.
18. **NDVI Pearson zayıf (0.05) ama Spearman -0.25** — non-lineer ilişki; RF yakaladı ama lineer modeller kaçırdı.
19. **2022 ekstrem ısı yılı yerel rüzgar değişiminden değil** — ERA5 wind speed analizi gösterdi ki 2022'de rüzgar normal, sıcaklık 2.81°C anomali → küresel ısı dalgası.

## Akademik Sınırlılıklar (Dürüstçe Raporlanan)

20. **Out-of-area extrapolation zayıf** (Hold-out R²=0.10) — model **pilot içi** kullanılmalı, başka şehre transfer için lokal kalibrasyon gerekir.
21. **MODIS uydu doğrulaması başarısız** — MODIS 1km, pilot 5×5 km = 25 piksel max → istatistiksel anlamlı karşılaştırma yapılamadı (n=34, r=0.08). Sentinel-3 SLSTR sonraki çalışma.
22. **Residual mekânsal otokorelasyon** (Moran I=0.66) — model UHI'ın %18'ini açıkladı, %82 residual'da kaldı. **Çözüm denendi (spatial lag) ama target leakage** çıktı (R²=0.99 ama production'da kullanılamaz). Gerçek çözüm: GWRF veya RF-kriging hibrit (sonraki çalışma).
23. **TS 9111 konut varsayımı** — tüm binalar 3.0 m/kat (gerçekte ticaret 3.5, sanayi 4.5).
24. **5-yıl medyan statik** — yıllar arası dinamik feature'lar (NDVI/Albedo) kullanılmadı.

## Üretilen Ürünler

25. **GitHub repo:** `github.com/ercntrgt/asliutpm` — 25 commit, açık kaynak, akademik dürüst.
26. **11 Jupyter notebook** (00 → 10) sıralı analiz akışı.
27. **15 Python modülü** (`src/` altında, paket olarak install edilebilir).
28. **31 görsel** (figures/ — bu dosyada akışı var).
29. **17 özet tablo** (CSV).
30. **8 GeoPackage** son ürün (modelleme tablosu, tahminler, UTPM, persistence, priority).
31. **Streamlit web uygulaması** + Claude API yorumlu karar destek aracı.
32. **14 markdown tez materyali** (tez/ klasörü) — bu dosya dahil.

## En Önemli Tek Cümle

> **Konyaaltı'nın %3.1'i (881 hücre, 0.79 km²) son 5 yılda sürekli en sıcak quartile'da kalmış UHI çekirdeğidir; modelimiz albedo, NDVI ve gradient yapılaşma probabilitesini kullanarak bu kalıcı sıcak alanları %87 doğrulukla tahmin etmektedir.**

---

# BÖLÜM 2 — GÖRSEL AKIŞI (Tez Bölümü × Görsel × Anlam)

> 31 görsel × hangi tez bölümünde × ne anlatır × hangi sayıyı destekler.
> Görseller `figures/` klasöründe.

## Tez Yapısı (Önerilen)

```
1. GİRİŞ
   1.1 Problem (Konyaaltı UHI)
   1.2 Hedef (UTPM)
   1.3 Katkı

2. LİTERATÜR
   (görsel yok — yazılı)

3. VERİ VE YÖNTEM
   3.1 Çalışma alanı
   3.2 Veri kaynakları
   3.3 Önişleme
   3.4 Modelleme
   3.5 Doğrulama

4. SONUÇLAR
   4.1 Tanımlayıcı istatistikler
   4.2 Korelasyon ve VIF
   4.3 RF model performans
   4.4 SHAP açıklanabilirlik
   4.5 UTPM indeksi ve LISA
   4.6 Persistence (yıllar arası)
   4.7 Karar destek katmanı
   4.8 Akademik sağlamlık (baselines + CI)
   4.9 Dış doğrulama

5. TARTIŞMA
   5.1 Tezsel katkı
   5.2 Sınırlılıklar
   5.3 Sonraki çalışma

6. SONUÇ ve ÖNERİLER
   6.1 Şehir planlamacısına öneriler
   6.2 Politika önerileri
```

---

## 3.1 — Çalışma Alanı

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `00_kat_histogram.png` | Konyaaltı imar veri seti, kat sayısı dağılımı (n=17,506) | Veri kaynağı tanımı; "İmar verisinde 1-36 kat aralığında dağılım" |
| `00_pilot_alan_dagilim.png` | İki panel: Konyaaltı geneli mahalle dağılımı + pilot 15 mahalle | Pilot bölge tanımı; mahalle isimleri figürde işaretli |
| `01_grid_overview.png` | Pilot sınır + 100m grid + 30m vs 100m hizalanma | Yöntem akış: "30 m analitik + 100 m planlama grid'leri kuruldu" |

---

## 3.2 — Veri Kaynakları (Sıcaklık + Bağımsız Değişkenler)

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `02_lst_map.png` | Landsat 8/9 yaz medyan LST raster haritası | "Hedef değişken LST: 29.78-51.43°C, medyan 43.16°C" |
| `02_lst_histogram.png` | LST histogram + 30m grid choropleth | LST dağılımı + grid'e bağlanması gösterimi |
| `03_variables_maps.png` | 4 panel: LST + NDVI + Albedo + Impervious haritaları | Bağımsız değişkenlerin mekânsal dağılımı |
| `04_imputation_cv.png` | Bina yüksekliği imputation 5-fold CV (R²=0.957) | Yöntem: "Buffer cascade imputation kalitesi" |
| `04_building_overview.png` | 4 panel: imar yüksek/yapı yoğun/GHSL/scatter | Bina katmanı + GHSL doğrulama (median uyumlu) |
| `05_dtc_road_overview.png` | 6 panel: LST + DTC + yol + yapı + impervious + korelasyon matris | **Final feature haritaları** (7 değişken + LST birlikte) |
| `15_impervious_comparison.png` | ESA WorldCover (binary) vs Dynamic World (gradient) — 4 panel | "ESA binary kullanışsızdı, DW gradient eklendi" |

---

## 3.3 — Önişleme (Standardizasyon + Multicollinearity)

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `06_standardization_histograms.png` | 7 değişken × raw/log/z-skor dönüşüm öncesi-sonrası | "Skewed feature'lara log1p, hepsine z-skor" |
| `06_standardization_corr.png` | Z-skor korelasyon ısı haritası | Standardize edilmiş feature'ların ilişkisi |
| `07_correlation_matrix.png` | 7 z-skor + LST tam korelasyon matrisi | "Pairwise |r|<0.7, multicollinearity yok" |
| `07_vif_bars.png` | VIF bar chart (hepsi yeşil zonda <2) | "VIF max 1.78 (eşik 10), tüm değişkenler bağımsız" |

---

## 3.4 — Modelleme (RF Eğitim)

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `16_rf_v3_overview.png` | 4 panel: validation R² + SHAP importance + predicted map + residual map | **Ana RF performans görseli** (DW dahil 9 feature) |
| `16_dw_improvement.png` | Eski (8 feat) vs Yeni (10 feat) RF R² karşılaştırma | "DW feature ekleyerek R²: 0.85 → 0.87" |

---

## 3.5 — Doğrulama (5 Validation Katmanı)

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `17_baseline_comparison.png` | 5 model (Linear/Ridge/Lasso/GBM/RF) × R² + RMSE bar + CI95 | **Baseline karşılaştırma**: "RF +0.21 R² Lineer'den" |
| `17_feature_elimination.png` | Tam (10 feat) vs Minimal (7 feat) parsimony karşılaştırma | "ΔR²=-0.003 anlamsız → minimal model kabul" |
| `18_pdp.png` | 7 minimal feature × LST partial dependence eğrileri | **Açıklanabilirlik**: NDVI 0-0.3 dik düşüş, vb. |
| `18_shap_interactions.png` | 7×7 etkileşim ısı haritası (NDVI×DW en güçlü 0.46) | Feature interaction analizi |
| `18_landsat_modis_validation.png` | 2 panel: scatter + Bland-Altman (Landsat × MODIS) | **MODIS başarısız doğrulama** — sınırlılık L12 raporu |

---

## 4.4 — SHAP Açıklanabilirlik

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `16_shap_v3_beeswarm.png` | SHAP beeswarm — her feature × her gözlem | **En kritik açıklanabilirlik görseli**; "Albedo 0.32, NDVI 0.25, DW 0.17, DTC 0.14..." |

---

## 4.5 — UTPM İndeks ve LISA

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `16_utpm_v3_overview.png` | 4 panel: UTPM continuous + Jenks 5-sınıf + LISA + UTPM ağırlıklar bar | **UTPM ana sonuç görseli** |
| `10_persistence_vs_utpm.png` | UTPM × persistence scatter + boxplot | "UTPM × Q4 yıl sayısı r=0.33" |
| `11_blockage_overview.png` | Wind Blockage Index haritası + LST scatter | Hafta 17 ek katman (rüzgar blokajı) |

---

## 4.6 — Persistence (Yıllar Arası)

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `09_cross_year_overview.png` | 4 panel: yıllık R² + LST korelasyon + persistent hot + std | **Persistence ana görseli**: "5 yıl mean korelasyon 0.905" |
| `09_yearly_lst_maps.png` | 5 yıl × LST haritası + 5-yıl mean | Yıllık LST görsel doğrulama; 2022 anomali |
| `13_lst_wind_temporal.png` | Yıllık LST × wind speed çift y-axis + scatter | "2022 sıcak dalga rüzgar kaynaklı değil" |
| `12_era5_wind_rose.png` | ERA5 yön histogram + polar wind rose | Rüzgar yönü kalibrasyonu (165° vs ERA5 159°) |

---

## 4.7 — Karar Destek Katmanı

| Görsel | İçerik | Tezdeki kullanım |
|---|---|---|
| `14_bivariate_decision.png` | 3 panel: bivariate harita + priority harita + 3×3 legend matrix | **Şehir planlamacısı 9 sınıflık eylem haritası** |

---

## 5 — Tartışma / Sınırlılıklar

(Çoğunlukla yazılı; bazı görseller tekrar referans verilir:)

- L12 (MODIS başarısız) → `18_landsat_modis_validation.png`
- L13 (residual autocorrelation) → `16_rf_v3_overview.png` residual paneli
- L14 (spatial lag leakage) → tablo + tez/14 metni

---

## ÖZET TABLO — Görsel Sıralaması (Tezde Sırayla)

| Bölüm | # Görsel | Görsel adları |
|---|---|---|
| 3.1 Çalışma Alanı | 3 | 00_kat_histogram, 00_pilot_alan_dagilim, 01_grid_overview |
| 3.2 Veri Kaynakları | 7 | 02_lst_map, 02_lst_histogram, 03_variables_maps, 04_imputation_cv, 04_building_overview, 05_dtc_road_overview, 15_impervious_comparison |
| 3.3 Önişleme | 4 | 06_standardization_histograms, 06_standardization_corr, 07_correlation_matrix, 07_vif_bars |
| 3.4 Modelleme | 2 | 16_rf_v3_overview, 16_dw_improvement |
| 3.5 Doğrulama | 5 | 17_baseline_comparison, 17_feature_elimination, 18_pdp, 18_shap_interactions, 18_landsat_modis_validation |
| 4.4 SHAP | 1 | 16_shap_v3_beeswarm |
| 4.5 UTPM/LISA | 3 | 16_utpm_v3_overview, 10_persistence_vs_utpm, 11_blockage_overview |
| 4.6 Persistence | 4 | 09_cross_year_overview, 09_yearly_lst_maps, 13_lst_wind_temporal, 12_era5_wind_rose |
| 4.7 Karar Destek | 1 | 14_bivariate_decision |
| 5 Tartışma | (referans) | 03_variables_corr (ek korelasyon detayı) |

**Toplam:** 31 görsel — silinen 9 redundant. Hepsi `figures/` altında.

---

## TABLO İNDEKSİ (Tez Bölümleri ile Eşleştirme)

| Tablo | Bölüm | İçerik |
|---|---|---|
| `00_mahalle_kapsama.csv` | 3.1 | Mahalle başına imar nokta dağılımı |
| `00_pilot_alan_kapsama.csv` | 3.1 | Pilot 15 mahalle kapsama özeti |
| `01_grid_summary.csv` | 3.1 | Grid metrikleri (28K hücre, alan, hizalanma) |
| `02_lst_summary.csv` | 3.2 | LST kompozit (sahne sayısı, range) |
| `03_variables_summary.csv` | 3.2 | 4 değişken × LST korelasyon |
| `04_building_summary.csv` | 3.2 | Imputation CV + GHSL doğrulama |
| `05_dtc_road_summary.csv` | 3.2 | 7 değişken × LST korelasyon |
| `06_standardization_summary.csv` | 3.3 | Skewness + log/z |
| `07_vif_analysis.csv` | 3.3 | VIF + Pearson + Spearman |
| `08_rf_metrics.csv` | 3.5 | 4 validation katman skoru |
| `09_cross_year_metrics.csv` | 4.6 | Yıl-by-yıl RMSE/MAE/R² |
| `10_utpm_weights.csv` | 4.5 | 7 feature SHAP ağırlığı |
| `10_utpm_stats.csv` | 4.5 | UTPM × LST/persistence + Moran I |
| `12_era5_wind_calibration.csv` | 4.6 | ERA5 yön kalibrasyonu özeti |
| `12_era5_hourly_wind.csv` | (ek) | 1840 saat raw veri |
| `13_lst_wind_yearly.csv` | 4.6 | Yıllık LST × wind speed |
| `14_priority_summary.csv` | 4.7 | 9 öncelik özet (4220 acil, 6242 koruma) |
| `16_dw_comparison.csv` | 3.4 | ESA → DW iyileşme tablo |
| `17_baseline_comparison.csv` | 3.5 | 5 model × CI95 |
| `17_hyperparameter_tuning.csv` | 3.5 | 18 grid kombinasyonu |
| `17_feature_elimination.csv` | 3.5 | Tam vs minimal |
| `18_external_validation.csv` | 3.5 | MODIS + OOT + residual Moran |
| `19_spatial_rf_comparison.csv` | 5.2 (sınırlılık) | Hafta 22 vs 24 (leakage demo) |

---

## TEZ MARKDOWN MATERYALLERİ

`tez/` klasörü altında 14 markdown:

| Dosya | Tez bölümüne katkı |
|---|---|
| `00_PROJE_OZET_VE_GORSEL_AKISI.md` | (bu dosya) — sunum + akış |
| `01_executive_summary.md` | Özet (tezin ilk sayfası materyali) |
| `02_methodology.md` | Bölüm 3 yöntem akışı + mermaid şema |
| `03_results.md` | Bölüm 4 master sayısal tablolar |
| `04_limitations.md` | Bölüm 5.2 sınırlılıklar (14 madde) |
| `05_recommendations.md` | Bölüm 6 şehir planlamacısına öneriler |
| `06_figures_tables_index.md` | (eski indeks; bu dosya yeni master) |
| `07_blockage_addition.md` | 3.2/4.5 wind blockage entegrasyonu |
| `08_era5_calibration.md` | 4.6 ERA5 doğrulama |
| `09_wind_speed_temporal.md` | 4.6 2022 outlier yorum |
| `10_bivariate_decision_layer.md` | 4.7 karar destek katmanı |
| `11_dynamic_world_upgrade.md` | 3.2/3.4 DW yükseltmesi |
| `12_robustness_baselines.md` | 3.5 baselines + CI + parsimony |
| `13_external_validation.md` | 3.5 MODIS + OOT + PDP + interactions |
| `14_spatial_rf.md` | 5.2 spatial lag leakage demo |

---

**Kullanım:** Tez yazarken bu dosyayı referans olarak kullanın. Her görselin **dosya adı + sayfa içi yer + bağlantılı sayı** belirtilmiştir. Tablolar için aynı şekilde.
