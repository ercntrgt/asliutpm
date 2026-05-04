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
