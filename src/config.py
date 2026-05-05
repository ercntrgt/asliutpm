"""Proje genelinde kullanılan sabitler.

Tüm yollar, CRS, mahalle listesi, model parametreleri burada.
Magic number kullanmayın — gerekli sabit yoksa buraya ekleyin.
"""
import os
from pathlib import Path

# --- Yollar ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_GRID = PROJECT_ROOT / "data" / "grid"
DATA_EXTERNAL = PROJECT_ROOT / "data" / "external"
RESULTS = PROJECT_ROOT / "results"
FIGURES = PROJECT_ROOT / "figures"
TABLES = PROJECT_ROOT / "tables"

# --- Coğrafi referans ---
CRS_PROJECTED = "EPSG:32636"   # WGS84 / UTM 36N — Antalya
CRS_GEOGRAPHIC = "EPSG:4326"   # WGS84 lat/lon

# --- Çalışma alanı (15 mahalleli kentleşmiş sahil koridoru) ---
PILOT_NEIGHBORHOODS = [
    "UNCALI", "ULUÇ", "HURMA", "MOLLA YUSUF", "ÖĞRETMENEVLERİ",
    "TOROS", "SİTELER", "LİMAN", "GÜRSU", "ARAPSUYU",
    "KUŞKAVAĞI", "PINARBAŞI", "AKKUYU", "ALTINKUM", "SARISU",
]

# --- Grid çözünürlükleri ---
GRID_ANALYTIC_M = 30    # Analitik modelleme grid'i
GRID_PLANNING_M = 100   # Planlama karar destek grid'i

# --- Kat -> metre dönüşümü (TS 9111) ---
FLOOR_HEIGHT_M = {
    "konut": 3.0,
    "ticaret": 3.5,
    "sanayi": 4.5,
    "default": 3.0,
}

# --- LST kompozit dönemi ---
LST_YEARS = [2020, 2021, 2022, 2023, 2024]
LST_MONTHS = [6, 7, 8]            # Haziran-Ağustos
CLOUD_COVER_THRESHOLD = 10        # % — Landsat sahne filtresi

# --- DTC_breeze (rüzgar-yönelimli kıyı mesafesi) ---
WIND_FROM_DEG = 165               # ERA5 doğrulamadan önce başlangıç varsayımı (SSE)
DTC_MAX_DISTANCE_M = 20000

# --- Random Forest ---
RANDOM_STATE = 42
RF_N_ESTIMATORS = 500
TEST_SIZE = 0.20

# --- Buffer cascade (bina yüksekliği imputation) ---
BUFFER_CASCADE_M = [10, 100, 500, 1000]
MIN_NEIGHBORS_FOR_IMPUTATION = 3

# --- Excel kaynağı ---
IMAR_XLSX = DATA_RAW / "konyaalti_imar_tum_veri.xlsx"
IMAR_SHEET = "konyaalti_imar_tum_veri (2)"

# --- Google Earth Engine ---
# Kullanıcının Cloud project ID'si. PowerShell'de set:
#   $env:GEE_PROJECT = "ee-ercangpg"
# Kalıcı set:
#   [Environment]::SetEnvironmentVariable("GEE_PROJECT", "ee-ercangpg", "User")
GEE_PROJECT: str | None = os.environ.get("GEE_PROJECT")

# --- LST raster çıktıları ---
LST_RASTER = DATA_PROCESSED / "lst_summer_median_2020_2024.tif"
LST_GRID_30M = DATA_PROCESSED / "grid_30m_lst.gpkg"

# --- Sentinel-2 (NDVI + Albedo) ---
S2_YEARS = [2020, 2021, 2022, 2023, 2024]
S2_MONTHS = [6, 7, 8]
S2_CLOUD_THRESHOLD = 20            # Sentinel-2 daha sık geçer, eşik daha gevşek
NDVI_RASTER = DATA_PROCESSED / "ndvi_summer_median_2020_2024.tif"
ALBEDO_RASTER = DATA_PROCESSED / "albedo_summer_median_2020_2024.tif"

# --- ESA WorldCover (Geçirimsiz yüzey) ---
WORLDCOVER_VERSION = "v200"        # v200 = 2021, v100 = 2020
IMPERVIOUS_RASTER = DATA_PROCESSED / "impervious_esa_worldcover_2021.tif"

# --- Birleştirilmiş 30m grid (LST + NDVI + Albedo + Impervious) ---
GRID_30M_VARIABLES = DATA_PROCESSED / "grid_30m_variables.gpkg"

# --- Hafta 5: Bina yüksekliği + GHSL doğrulama ---
BUILDINGS_IMPUTED = DATA_PROCESSED / "buildings_pilot_imputed.gpkg"
GHSL_BUILT_H_RASTER = DATA_PROCESSED / "ghsl_built_h_2018.tif"
GHSL_YEAR = 2018
GRID_30M_BUILDING = DATA_PROCESSED / "grid_30m_building.gpkg"

# --- Hafta 6: DTC_breeze + yol yoğunluğu ---
COASTLINE_GPKG = DATA_PROCESSED / "osm_coastline.gpkg"
ROADS_GPKG = DATA_PROCESSED / "osm_roads.gpkg"
GRID_30M_FULL = DATA_PROCESSED / "grid_30m_full.gpkg"  # 7 değişkenin tümü

# --- Hafta 8: Standardizasyon ---
GRID_30M_STANDARDIZED = DATA_PROCESSED / "grid_30m_standardized.gpkg"
SKEW_THRESHOLD_LOG = 1.0   # |skew| > bu değer ⇒ log1p uygula

# 7 bağımsız değişken — modelleme için kanonik liste
FEATURE_COLUMNS = [
    "ndvi_mean",
    "albedo_mean",
    "impervious_pct",
    "building_height_mean",
    "building_density_per_km2",
    "road_density_m_per_km2",
    "dtc_breeze_m",
]
TARGET_COLUMN = "lst_mean"

# --- Hafta 9: Feature seçimi ---
VIF_THRESHOLD = 10.0
GRID_30M_MODELING = DATA_PROCESSED / "grid_30m_modeling.gpkg"

# Notebook 07 sonrası karar: VIF analizi multicollinearity göstermediği için
# 7 değişkenin tümü modelde tutulacak. Random Forest Hafta 10'da feature
# importance ile zayıf prediktörleri yorumlayacak.
SELECTED_FEATURES = list(FEATURE_COLUMNS)  # tüm 7

# --- Hafta 10: Random Forest + validation ---
PREDICTIONS_GPKG = DATA_PROCESSED / "grid_30m_predictions.gpkg"
MODEL_PKL = RESULTS / "rf_model.pkl"
RF_VALIDATION_JSON = RESULTS / "rf_validation.json"
SPATIAL_CV_BLOCK_M = 500          # mekânsal blok CV hücre boyutu
HOLDOUT_NEIGHBORHOODS = ["ALTINKUM", "HURMA", "GÜRSU"]   # 3 mahalle hold-out
DTC_SATURATED_THRESHOLD = 19999   # bu değerin üstü saturated sayılır

# --- Hafta 11: Yıllar arası CV ---
LST_YEARLY_RASTERS = {
    y: DATA_PROCESSED / f"lst_summer_{y}.tif" for y in LST_YEARS
}
GRID_30M_YEARLY = DATA_PROCESSED / "grid_30m_yearly_lst.gpkg"
CROSS_YEAR_VALIDATION_JSON = RESULTS / "cross_year_validation.json"
PERSISTENCE_GPKG = DATA_PROCESSED / "grid_30m_persistence.gpkg"

# --- Hafta 12-13: SHAP + UTPM lineer indeks + mekânsal analiz ---
SHAP_VALUES_NPY = RESULTS / "shap_values.npy"
SHAP_SAMPLE_GPKG = DATA_PROCESSED / "grid_30m_shap_sample.gpkg"
UTPM_GPKG = DATA_PROCESSED / "grid_30m_utpm.gpkg"
UTPM_RESULTS_JSON = RESULTS / "utpm_analysis.json"
SHAP_SAMPLE_N = 1000              # SHAP hesabı için örneklem (approximate=True ile)
MORAN_K_NEIGHBORS = 8             # Moran'a giren k-NN
JENKS_K_CLASSES = 5               # UTPM sınıf sayısı

# UTPM yön çevirme: NDVI yüksek = serin → çevir
# Diğer feature'lar pozitif (yüksek değer = sıcak); RF importance'ları zaten yön bağımsız.
UTPM_SIGN_FLIPS = {
    "ndvi_mean_z": -1,            # yüksek NDVI = serin
    "dtc_breeze_m_z": +1,         # yüksek DTC = sıcak (kara içi), ama saturated outlier var
}
