# Yöntem Akışı

## 16 Haftalık Pipeline

```mermaid
flowchart TD
    A[Hafta 1: İmar Excel<br/>43,423 nokta + DMS koordinat] --> B[Hafta 2: Pilot sınır<br/>concave hull union<br/>30m + 100m grid<br/>28,247 + 2,906 hücre]
    B --> C[Hafta 3: Landsat LST<br/>2020-2024 yaz medyan<br/>71 sahne, bulut<%10]
    B --> D[Hafta 4: Sentinel-2<br/>NDVI + Albedo Liang 2001<br/>ESA WorldCover impervious]
    B --> E[Hafta 5: Bina yüksekliği<br/>kat × 3.0m + buffer cascade<br/>CV R²=0.957<br/>GHSL doğrulama]
    B --> F[Hafta 6: DTC_breeze<br/>OSM coastline ray casting<br/>165° SSE<br/>OSM yol yoğunluğu]

    C --> G[grid_30m_full.gpkg<br/>7 değişken + LST<br/>28,247 satır]
    D --> G
    E --> G
    F --> G

    G --> H[Hafta 8: Standardizasyon<br/>log1p skew>1<br/>z-score]
    H --> I[Hafta 9: VIF analizi<br/>max 1.78 → temiz<br/>7 değişkenin tümü]
    I --> J[Hafta 10: Random Forest<br/>500 ağaç, 8 feature<br/>4 validation katmanı]

    J --> K[Hafta 11: Yıllar arası CV<br/>5 yıl LST<br/>persistence skorları]
    J --> L[Hafta 12-13: SHAP + UTPM<br/>lineer indeks 0-100<br/>Moran's I + LISA<br/>Jenks 5 sınıf]

    K --> M[grid_30m_persistence.gpkg<br/>2,008 persistent HOT<br/>3,390 persistent COLD]
    L --> N[grid_30m_utpm.gpkg<br/>UTPM + sınıf + LISA<br/>FINAL ÜRÜN]

    M --> O[Hafta 14-15: Streamlit<br/>folium harita + Claude API<br/>karar destek prototipi]
    N --> O

    style J fill:#E76F51
    style L fill:#E76F51
    style N fill:#2A9D8F
    style O fill:#2A9D8F
```

## Veri akış zinciri

| Hafta | Girdi | İşlem | Çıktı |
|---|---|---|---|
| 1 | Konyaaltı imar Excel | DMS koord parse, mahalle filtre | `imar_pilot_*.gpkg` |
| 2 | Pilot noktalar | Concave hull union + 30/100m grid | `grid_30m.gpkg`, `grid_100m.gpkg`, `pilot_boundary.gpkg` |
| 3 | GEE Landsat 8/9 C2L2 | Bulut maskesi + ST_B10 → Celsius + median | `grid_30m_lst.gpkg` |
| 4 | GEE S2 + WorldCover | NDVI/Albedo/Impervious zonal | `grid_30m_variables.gpkg` |
| 5 | İmar kat verisi + GHSL | Buffer cascade imputation + 5-fold CV | `grid_30m_building.gpkg` |
| 6 | OSM coastline + roads | Ray casting + overlay | `grid_30m_full.gpkg` |
| 8 | full GPKG | log1p + z-score | `grid_30m_standardized.gpkg` |
| 9 | standardized | VIF analizi | `grid_30m_modeling.gpkg` |
| 10 | modeling | RF + 4 validation | `grid_30m_predictions.gpkg`, `rf_model.pkl` |
| 11 | RF model + 5 yıl LST | Cross-year prediction | `grid_30m_persistence.gpkg` |
| 12-13 | model + features | SHAP + UTPM + Moran + Jenks | `grid_30m_utpm.gpkg` |
| 14-15 | UTPM + persistence | Streamlit + folium + Claude | `streamlit_app/` |

## Yazılım katmanları

```
src/
├── config.py              # Tüm sabitler (CRS, mahalleler, RF parametre)
├── coord_utils.py         # DMS parser
├── grid_utils.py          # Pilot sınır + grid kurulum
├── building_height.py     # Imputation + grid agregasyon
├── variables.py           # Zonal stats
├── dtc_breeze.py          # Ray casting + OSM
├── gee_utils.py           # GEE auth + Landsat/S2/WorldCover/GHSL
├── standardization.py     # Skewness + z-score
├── feature_selection.py   # VIF + iterative drop
├── modeling.py            # RF + 4 validation
└── utpm.py                # SHAP + indeks + Moran + Jenks
```

## Önemli yöntem detayları

### Buffer cascade imputation (Hafta 5)
- 5,787 / 18,575 noktada kat verisi eksik
- Her eksik nokta için 10 m → 100 m → 500 m → 1000 m halkalarında en az 3 komşu olan en küçük yarıçapta ortalama yükseklik atanır
- 5-fold CV: RMSE = 0.81 m, R² = 0.957

### DTC_breeze (Hafta 6)
- Hakim rüzgar 165° SSE (literatür/iklim atlas)
- Her grid hücre centroidinden 165° yönünde 20 km'lik ışın
- OSM coastline ile ilk kesişim mesafesi = DTC_breeze
- 1,066 hücre saturated (kıyının deniz tarafında, ışın denize gidiyor)

### Random Forest (Hafta 10)
- `RandomForestRegressor(n_estimators=500, random_state=42, n_jobs=-1)`
- 8 feature (7 raw + `is_dtc_saturated` binary flag)
- NaN handling: `fillna(0)` (semantic — bina yok = 0 m yükseklik)

### Validation katmanları
1. **Random 5-fold KFold** — `shuffle=True, random_state=42`
2. **Spatial Block 5-fold** — 500 m karelere böl, blokları rastgele fold'a ata
3. **Mahalle hold-out** — `["ALTINKUM", "HURMA", "GÜRSU"]` tamamen test
4. **Permutation null** — target shuffled, 50 perm × 3-fold CV

### SHAP TreeExplainer (Hafta 12)
- `feature_perturbation="tree_path_dependent"`, `approximate=True`
- 1000 sample (28K full hesap saatlerce sürer)
- Global importance = `mean(|shap_values|)` → normalize edilmiş ağırlık

### UTPM indeks
- `UTPM_raw = Σ_i sign_i × w_i × z_i` (i = 7 feature)
- `sign_flips = {ndvi_z: -1}` (yüksek NDVI = serin → çevir)
- `UTPM_score = (raw - min) / (max - min) × 100` (0-100)

### Moran's I + LISA
- K=8 en yakın komşu, row-standardize W matrisi
- `esda.Moran` global, `Moran_Local` LISA
- LISA cluster: HH/LL/HL/LH eğer p_sim < 0.05, yoksa NS

### Jenks Natural Breaks
- `mapclassify.NaturalBreaks(values, k=5)`
- Sınıf etiketleri: Çok serin / Serin / Orta / Sıcak / Çok sıcak

## Tekrar üretilebilirlik

Tüm rasgele seedler `RANDOM_STATE = 42`. Tüm CRS `EPSG:32636` (UTM 36N). Tüm yıllar 2020-2024 yaz Haziran-Ağustos.

```bash
git clone https://github.com/ercntrgt/asliutpm.git
cd asliutpm
conda env create -f environment.yml
conda activate utpm
pip install -e .

# data/raw/konyaalti_imar_tum_veri.xlsx dosyasını yerleştir
# GEE_PROJECT env variable set et
# Sonra notebook'ları sırayla çalıştır:
jupyter lab notebooks/00_data_overview.ipynb
# ... 01, 02, ..., 10
```
