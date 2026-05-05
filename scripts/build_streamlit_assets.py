"""Streamlit Cloud için asset üretici — 30m PNG choropleth + slim GPKG.

Çalıştırma:
    conda run -n utpm python scripts/build_streamlit_assets.py

Çıktılar:
    streamlit_app/data/utpm_choropleth.png   — Jenks 5-sınıf renkli raster
    streamlit_app/data/utpm_bbox.json        — Folium ImageOverlay için bbox
    streamlit_app/data/grid_30m_full.gpkg    — tek consolidated lookup tablosu
    streamlit_app/data/pilot_boundary.gpkg   — pilot sınır
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import geopandas as gpd
from PIL import Image
import rasterio
from rasterio import Affine
from rasterio.features import rasterize
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scipy.ndimage import distance_transform_edt

from src.config import (
    DATA_GRID, DATA_PROCESSED,
    UTPM_GPKG, PERSISTENCE_GPKG, GRID_30M_FULL, PRIORITY_GPKG,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "streamlit_app" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Streamlit asset üretici — 30m PNG + slim GPKG")
print("=" * 60)

# ============================================================
# 1. Slim consolidated GPKG (lookup için)
# ============================================================
print("\n[1/3] Consolidated GPKG hazırlanıyor...")

utpm = gpd.read_file(UTPM_GPKG)
persist = gpd.read_file(PERSISTENCE_GPKG)
features = gpd.read_file(GRID_30M_FULL)
priority = gpd.read_file(PRIORITY_GPKG)

merged = utpm[["cell_id", "lst_mean", "utpm_score", "utpm_class",
               "lisa_cluster", "geometry"]].copy()
merged = merged.merge(
    persist[["cell_id", "lst_yearly_mean", "lst_yearly_std",
             "years_in_top_quartile", "years_in_bottom_quartile"]],
    on="cell_id", how="left",
)
feat_cols = ["cell_id", "ndvi_mean", "albedo_mean", "dw_built_pct",
             "building_height_mean", "road_density_m_per_km2",
             "dtc_breeze_m", "wind_blockage_index"]
merged = merged.merge(
    features[[c for c in feat_cols if c in features.columns]],
    on="cell_id", how="left",
)
merged = merged.merge(
    priority[["cell_id", "priority_label"]],
    on="cell_id", how="left",
)

# Mahalle bilgisi
imar = gpd.read_file(DATA_PROCESSED / "imar_pilot.gpkg")
joined = gpd.sjoin_nearest(
    merged[["cell_id", "geometry"]],
    imar[["mahalle", "geometry"]],
    how="left", max_distance=200,
)
mahalle_per_cell = joined.groupby("cell_id")["mahalle"].first()
merged["mahalle"] = merged["cell_id"].map(mahalle_per_cell)

# Numerik kolonları yuvarla (boyut)
for col in merged.select_dtypes(include=[np.float64]).columns:
    merged[col] = merged[col].round(3)

# Float kolonlar dahi int'lere zorlama yapmayalım — geometri korunsun
out_gpkg = OUT_DIR / "grid_30m_full.gpkg"
merged.to_file(out_gpkg, driver="GPKG")
print(f"  saved: {out_gpkg.name} ({out_gpkg.stat().st_size/1024/1024:.2f} MB)")
print(f"  cells: {len(merged):,}, cols: {len(merged.columns)}")

# Boundary — Streamlit overlay için DELİKSİZ dış kabuğu kaydet
# (iç delik etrafına teal çizgi çizilmesin, doldurduğumuz parklar düzgün görünsün)
from shapely.geometry import Polygon, MultiPolygon
boundary = gpd.read_file(DATA_GRID / "pilot_boundary.gpkg")

def _outer_only(geom):
    if isinstance(geom, Polygon):
        return Polygon(geom.exterior)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])
    return geom

boundary_outer = boundary.copy()
boundary_outer["geometry"] = boundary_outer.geometry.apply(_outer_only)
out_bnd = OUT_DIR / "pilot_boundary.gpkg"
boundary_outer.to_file(out_bnd, driver="GPKG")
print(f"  saved: {out_bnd.name} ({out_bnd.stat().st_size/1024:.1f} KB) — deliksiz dış kabuk")

# ============================================================
# 2. PNG Choropleth Raster (30m UTM → 4326 reproject)
# ============================================================
print("\n[2/3] PNG choropleth üretiliyor...")

utpm_utm = merged.to_crs("EPSG:32636").copy()
bounds_utm = utpm_utm.total_bounds  # [w, s, e, n]
res = 30
width = int(np.ceil((bounds_utm[2] - bounds_utm[0]) / res))
height = int(np.ceil((bounds_utm[3] - bounds_utm[1]) / res))
print(f"  UTM raster: {width} × {height} piksel, 30m res")

transform_utm = Affine(res, 0, bounds_utm[0],
                       0, -res, bounds_utm[3])

# utpm_class -1/NaN olanları 5 (background) yap
classes = utpm_utm["utpm_class"].fillna(-1).astype(int).values
shapes_iter = ((geom, int(cls) if cls >= 0 else 255)
               for geom, cls in zip(utpm_utm.geometry, classes))

arr_utm = rasterize(
    shapes_iter,
    out_shape=(height, width),
    transform=transform_utm,
    fill=255,
    dtype=np.uint8,
)
print(f"  rasterize: unique values = {np.unique(arr_utm)}")

# --- Sınır içi boş pikselleri (park/yol/dere) komşu UTPM ile doldur ---
# Boundary'nin DELİKSİZ dış kabuğunu mask olarak kullan (yukarıda tanımlandı).
boundary_utm = boundary.to_crs("EPSG:32636")
outer_geoms = [_outer_only(g) for g in boundary_utm.geometry]
mask_utm = rasterize(
    [(g, 1) for g in outer_geoms],
    out_shape=(height, width),
    transform=transform_utm,
    fill=0,
    dtype=np.uint8,
)

valid = arr_utm != 255
empty_inside = (arr_utm == 255) & (mask_utm == 1)
n_empty = int(empty_inside.sum())
n_total_inside = int(mask_utm.sum())
if n_empty > 0 and valid.any():
    _, (yi, xi) = distance_transform_edt(~valid, return_indices=True)
    arr_utm = arr_utm.copy()
    arr_utm[empty_inside] = arr_utm[yi[empty_inside], xi[empty_inside]]
    print(f"  fill: {n_empty:,} / {n_total_inside:,} sınır içi delik "
          f"({n_empty/n_total_inside*100:.1f}%) komşu UTPM ile dolduruldu")
else:
    print(f"  fill: doldurulacak boş piksel yok")

# Reproject UTM → 4326 (Folium için)
src_crs = "EPSG:32636"
dst_crs = "EPSG:4326"
dst_transform, dst_width, dst_height = calculate_default_transform(
    src_crs, dst_crs, width, height, *bounds_utm,
)
arr_4326 = np.full((dst_height, dst_width), 255, dtype=np.uint8)
reproject(
    source=arr_utm,
    destination=arr_4326,
    src_transform=transform_utm,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.nearest,
)
print(f"  4326 raster: {dst_width} × {dst_height} piksel")

# Renk paleti — Jenks 5-sınıf + transparent background
# RGBA uint8
colors = np.array([
    [38, 70, 83, 220],     # 0 Çok serin (#264653)
    [42, 157, 143, 220],   # 1 Serin (#2A9D8F)
    [233, 196, 106, 220],  # 2 Orta (#E9C46A)
    [244, 162, 97, 220],   # 3 Sıcak (#F4A261)
    [231, 111, 81, 230],   # 4 Çok sıcak (#E76F51)
    [0, 0, 0, 0],          # 255 background → transparent
], dtype=np.uint8)

# 255'i 5'e map et palet için
arr_colored_idx = np.where(arr_4326 == 255, 5, arr_4326)
rgba = colors[arr_colored_idx]

# PNG kaydet
out_png = OUT_DIR / "utpm_choropleth.png"
Image.fromarray(rgba, mode="RGBA").save(out_png, optimize=True)
print(f"  saved: {out_png.name} ({out_png.stat().st_size/1024:.1f} KB)")

# Bbox JSON (Folium ImageOverlay için)
# dst_transform + dst_width/dst_height → 4326 bounds
west = dst_transform.c
north = dst_transform.f
east = west + dst_width * dst_transform.a
south = north + dst_height * dst_transform.e
bbox = {
    "south": float(south),
    "west": float(west),
    "north": float(north),
    "east": float(east),
    "width_px": int(dst_width),
    "height_px": int(dst_height),
}
out_bbox = OUT_DIR / "utpm_bbox.json"
with open(out_bbox, "w", encoding="utf-8") as f:
    json.dump(bbox, f, indent=2)
print(f"  saved: {out_bbox.name}")
print(f"  bbox: S={bbox['south']:.5f}, W={bbox['west']:.5f}, "
      f"N={bbox['north']:.5f}, E={bbox['east']:.5f}")

# ============================================================
# 3. Özet
# ============================================================
print("\n[3/3] Özet:")
total = sum(f.stat().st_size for f in OUT_DIR.iterdir() if f.is_file())
print(f"  Toplam streamlit_app/data: {total/1024/1024:.2f} MB")
for f in sorted(OUT_DIR.iterdir()):
    if f.is_file():
        size = f.stat().st_size
        if size < 1024 * 1024:
            print(f"    {f.name:40s} {size/1024:6.1f} KB")
        else:
            print(f"    {f.name:40s} {size/1024/1024:6.2f} MB")

print("\nDone.")
