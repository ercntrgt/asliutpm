# Görseller ve Tablolar İndeksi

## Görsel İndeksi

Toplam **18 PNG** görsel `figures/` altında. Tezde her görselin gerekçesi:

| Dosya | Hafta | Açıklama | Tezde nerede kullanılır |
|---|---|---|---|
| `00_kat_histogram.png` | 1 | İmar kat sayısı dağılımı (n=17,506 dolu) | Veri keşfi bölümü |
| `00_pilot_alan_dagilim.png` | 1 | Konyaaltı geneli + pilot alan nokta dağılımı | Veri keşfi bölümü |
| `01_grid_overview.png` | 2 | Pilot sınır + 100m grid + 30m vs 100m hizalanma | Yöntem — grid kurulumu |
| `02_lst_map.png` | 3 | Landsat yaz medyan LST raster (2020-2024) | Sonuçlar — sıcaklık dağılımı |
| `02_lst_histogram.png` | 3 | LST histogram + 30m grid choropleth | Sonuçlar — LST karakterizasyonu |
| `03_variables_maps.png` | 4 | 4 panel: LST + NDVI + Albedo + Impervious | Sonuçlar — feature haritaları |
| `03_variables_corr.png` | 4 | Korelasyon matrisi + LST scatter'lar | Sonuçlar — feature ilişkileri |
| `04_imputation_cv.png` | 5 | Buffer cascade 5-fold CV scatter + residual histogram | Yöntem — bina imputasyonu |
| `04_building_overview.png` | 5 | Bina yüksekliği + yapı yoğunluğu + GHSL + scatter | Sonuçlar — bina katmanı |
| `05_dtc_road_overview.png` | 6 | 6 panel: LST/DTC/yol/yapı/impervious + korelasyon | Sonuçlar — final feature haritaları |
| `06_standardization_histograms.png` | 8 | 7 değişken × raw/log/z dönüşüm öncesi-sonrası | Yöntem — standardizasyon |
| `06_standardization_corr.png` | 8 | Z-skor korelasyon ısı haritası | Yöntem |
| `07_correlation_matrix.png` | 9 | 7 z-skor + LST korelasyon | Yöntem — VIF analizi |
| `07_vif_bars.png` | 9 | VIF bar chart (hepsi yeşil zonda) | Yöntem |
| `08_rf_overview.png` | 10 | 4 panel: CV bars + importance + predicted + residual | Sonuçlar — RF performansı |
| `08_rf_feature_importance.png` | 10 | Gini vs Permutation importance bar | Sonuçlar — RF interpretation |
| `08_rf_actual_vs_predicted.png` | 10 | In-sample scatter (R²=0.846) | Sonuçlar — RF tahmin kalitesi |
| `09_cross_year_overview.png` | 11 | 4 panel: yıllık R² + LST korelasyon + persistent + std | Sonuçlar — yıllar arası |
| `09_yearly_lst_maps.png` | 11 | 5 yıllık LST haritası + 5-yıl mean | Sonuçlar — temporal kalıcılık |
| `10_shap_beeswarm.png` | 12 | SHAP beeswarm (her feature × her gözlem) | Sonuçlar — SHAP attribution |
| `10_shap_importance_bar.png` | 12 | SHAP global importance bar | Sonuçlar — SHAP global |
| `10_utpm_overview.png` | 13 | 4 panel: UTPM + Jenks + LISA + ağırlıklar | Sonuçlar — final ürün |
| `10_persistence_vs_utpm.png` | 13 | UTPM × persistence scatter + boxplot | Sonuçlar — doğrulama |

## Tablo İndeksi

Toplam **10 CSV** tablo `tables/` altında.

| Dosya | Hafta | İçerik | Tezde |
|---|---|---|---|
| `00_mahalle_kapsama.csv` | 1 | Mahalle bazlı imar kapsama (29 mahalle) | Veri keşfi tablo 1 |
| `00_pilot_alan_kapsama.csv` | 1 | Pilot 15 mahalle özet | Veri keşfi tablo 2 |
| `01_grid_summary.csv` | 2 | Pilot alan + grid metrikleri | Yöntem tablo |
| `02_lst_summary.csv` | 3 | LST kompozit özet (sahne sayısı, yıllar, range) | Sonuçlar tablo |
| `03_variables_summary.csv` | 4 | 4 feature × LST korelasyon + range | Sonuçlar tablo |
| `04_building_summary.csv` | 5 | Imputation CV + GHSL doğrulama | Yöntem tablo |
| `05_dtc_road_summary.csv` | 6 | 7 feature × LST korelasyon | Sonuçlar tablo |
| `06_standardization_summary.csv` | 8 | Skewness + log + z + Pearson + Spearman | Yöntem tablo |
| `07_vif_analysis.csv` | 9 | VIF + Pearson + Spearman karşılaştırma | Yöntem tablo |
| `08_rf_metrics.csv` | 10 | 4 validation katmanı RMSE/MAE/R² | Sonuçlar **kritik tablo** |
| `09_cross_year_metrics.csv` | 11 | Yıl-by-yıl RMSE/MAE/R² | Sonuçlar tablo |
| `10_utpm_weights.csv` | 13 | 7 feature SHAP ağırlığı | Sonuçlar tablo |
| `10_utpm_stats.csv` | 13 | UTPM × LST/Persistence + Moran I | Sonuçlar **kritik tablo** |

## Veri dosyaları (GeoPackage)

`data/processed/` altında **7 GPKG** + **9 GeoTIFF** + **2 OSM cache**.

| GPKG | Ana içerik |
|---|---|
| `imar_full.gpkg` | Tüm Konyaaltı 43,423 nokta |
| `imar_pilot*.gpkg` | Pilot 18,575 nokta (3 alt versiyon) |
| `grid_30m_full.gpkg` | 7 değişken + LST (modelleme öncesi) |
| `grid_30m_modeling.gpkg` | + log + z dönüşümleri |
| `grid_30m_predictions.gpkg` | RF tahmin + residual |
| `grid_30m_persistence.gpkg` | 5 yıl persistence skorları |
| `grid_30m_utpm.gpkg` | **Final ürün** (UTPM + Jenks + LISA) |

## Üretilen Python kodları

| Dosya | Hafta | İçerik |
|---|---|---|
| `src/config.py` | tüm | Sabitler |
| `src/coord_utils.py` | 1 | DMS parser |
| `src/grid_utils.py` | 2 | Pilot sınır + grid |
| `src/variables.py` | 4 | Zonal stats |
| `src/building_height.py` | 5 | Imputation + per-cell metrics |
| `src/dtc_breeze.py` | 6 | Ray casting + OSM |
| `src/gee_utils.py` | 3,4,5,11 | Earth Engine utilities |
| `src/standardization.py` | 8 | log + z |
| `src/feature_selection.py` | 9 | VIF |
| `src/modeling.py` | 10 | RF + 4 validation |
| `src/utpm.py` | 12-13 | SHAP + UTPM + Moran + Jenks |
| `streamlit_app/*.py` | 14-15 | Web prototipi (3 dosya) |

## Notebook'lar

| Notebook | Hafta | Hücre |
|---|---|---|
| `00_data_overview.ipynb` | 1 | 12 |
| `01_grid_setup.ipynb` | 2 | 11 |
| `02_lst.ipynb` | 3 | 11 |
| `03_variables.ipynb` | 4 | 15 |
| `04_building_height.ipynb` | 5 | 14 |
| `05_dtc_breeze.ipynb` | 6 | 10 |
| `06_standardization.ipynb` | 8 | 9 |
| `07_multicollinearity.ipynb` | 9 | 9 |
| `08_rf_model.ipynb` | 10 | 12 |
| `09_cross_year_validation.ipynb` | 11 | 8 |
| `10_shap_utpm.ipynb` | 12-13 | 12 |
