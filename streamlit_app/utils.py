"""Streamlit yardımcıları — slim consolidated GPKG (30m, online deploy için)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

# Backup: src/ klasörüne ulaşamayan deploy ortamı için
PROJECT_ROOT = APP_DIR.parent
if (PROJECT_ROOT / "src").exists():
    sys.path.insert(0, str(PROJECT_ROOT))


JENKS_LABELS = ["Çok serin", "Serin", "Orta", "Sıcak", "Çok sıcak"]
LISA_DESCRIPTIONS = {
    "HH": "Sıcak küme (UHI çekirdeği) — yüksek LST, yüksek LST'li komşular",
    "LL": "Serin küme — düşük LST, düşük LST'li komşular",
    "HL": "Yerel sıcak anomali — yüksek LST ama serin komşular",
    "LH": "Yerel serin anomali — düşük LST ama sıcak komşular",
    "NS": "İstatistiksel anlamlı küme yok",
}
PRIORITY_DESCRIPTIONS = {
    "1_ACIL_MUDAHALE": "Sıcak + Bloklu — çatı/sokak ağaçlandırma + bloklar arası açma",
    "2_YUKSEK_ONCELIK": "Sıcak + orta blokaj — çatı + sokak ağacı",
    "3_SICAK_ACIK": "Sıcak + açık (kıyı turist) — soğuk çatı + yansıtıcı yüzey",
    "4_BLOKLU_ORTA": "Orta sıcak + bloklu — bina aralık planlaması",
    "5_ORTA": "Orta sıcaklık + orta blokaj — izleme",
    "6_ORTA_ACIK": "Orta sıcak + açık — düşük öncelik müdahale",
    "7_BLOKLU_SERIN": "Serin + bloklu — gölge koruma",
    "8_SERIN_ORTA": "Serin + orta blokaj — izleme",
    "9_KORUMA": "Serin + açık — yeşil koridor koruma",
}

# Coğrafi referanslar (Streamlit'in bilmesi gereken)
CRS_GEOGRAPHIC = "EPSG:4326"
CRS_PROJECTED = "EPSG:32636"

# Modelleme feature'ları — slim GPKG'da olan kolon adları
SELECTED_FEATURES = [
    "ndvi_mean",
    "albedo_mean",
    "dw_built_pct",
    "building_height_mean",
    "road_density_m_per_km2",
    "dtc_breeze_m",
    "wind_blockage_index",
]
TARGET_COLUMN = "lst_mean"


def load_all_data() -> dict:
    """Tek consolidated GPKG'i yükler + bbox + boundary + raster yolu."""
    grid_path = DATA_DIR / "grid_30m_full.gpkg"
    boundary_path = DATA_DIR / "pilot_boundary.gpkg"
    bbox_path = DATA_DIR / "utpm_bbox.json"
    raster_path = DATA_DIR / "utpm_choropleth.png"

    grid = gpd.read_file(grid_path)
    boundary = gpd.read_file(boundary_path)
    with open(bbox_path, "r", encoding="utf-8") as f:
        bbox = json.load(f)

    return {
        "grid": grid,
        "boundary": boundary,
        "bbox": bbox,
        "raster_path": str(raster_path),
    }


def find_cell_by_coords(
    lat: float, lon: float, grid: gpd.GeoDataFrame,
) -> Optional[gpd.GeoSeries]:
    """Verilen lat/lon'a düşen 30 m grid hücresini döner (max 200 m tolerance)."""
    pt = (gpd.GeoSeries.from_xy([lon], [lat], crs=CRS_GEOGRAPHIC)
                       .to_crs(CRS_PROJECTED).iloc[0])
    grid_proj = grid.to_crs(CRS_PROJECTED) if grid.crs != CRS_PROJECTED else grid
    hits = grid_proj[grid_proj.geometry.contains(pt)]
    if len(hits) == 0:
        distances = grid_proj.distance(pt)
        idx = distances.idxmin()
        if distances.loc[idx] > 200:
            return None
        return grid_proj.loc[idx]
    return hits.iloc[0]


def cell_summary(cell_id: str, data: dict) -> dict:
    """Bir hücrenin tüm bilgi paketini döner (slim consolidated GPKG'den)."""
    grid = data["grid"]
    g = grid[grid["cell_id"] == cell_id]
    if g.empty:
        return {}
    g = g.iloc[0]

    summary = {
        "cell_id": cell_id,
        "lst_mean": float(g[TARGET_COLUMN]) if pd.notna(g.get(TARGET_COLUMN)) else None,
        "utpm_score": float(g["utpm_score"]) if pd.notna(g.get("utpm_score")) else None,
        "utpm_class": int(g["utpm_class"]) if pd.notna(g.get("utpm_class")) else -1,
        "utpm_class_label": (
            JENKS_LABELS[int(g["utpm_class"])]
            if 0 <= int(g.get("utpm_class", -1)) < len(JENKS_LABELS)
            else "?"
        ),
        "lisa_cluster": str(g.get("lisa_cluster", "NS")),
        "lisa_description": LISA_DESCRIPTIONS.get(str(g.get("lisa_cluster", "NS")), ""),
    }

    if "mahalle" in g.index and pd.notna(g["mahalle"]):
        summary["mahalle"] = str(g["mahalle"])

    # Features
    feat_dict = {}
    for col in SELECTED_FEATURES:
        if col in g.index and pd.notna(g[col]):
            feat_dict[col] = float(g[col])
    if feat_dict:
        summary["features"] = feat_dict

    # Persistence
    if "lst_yearly_mean" in g.index:
        summary["persistence"] = {
            "yearly_mean_lst": (
                float(g["lst_yearly_mean"]) if pd.notna(g["lst_yearly_mean"]) else None
            ),
            "yearly_std_lst": (
                float(g["lst_yearly_std"]) if pd.notna(g.get("lst_yearly_std")) else None
            ),
            "years_in_top_quartile": (
                int(g["years_in_top_quartile"])
                if pd.notna(g.get("years_in_top_quartile"))
                else 0
            ),
            "years_in_bottom_quartile": (
                int(g["years_in_bottom_quartile"])
                if pd.notna(g.get("years_in_bottom_quartile"))
                else 0
            ),
        }

    # Priority
    if "priority_label" in g.index and pd.notna(g["priority_label"]):
        pl = str(g["priority_label"])
        summary["priority"] = {
            "label": pl,
            "description": PRIORITY_DESCRIPTIONS.get(pl, ""),
            "wind_blockage_index": (
                float(g["wind_blockage_index"])
                if pd.notna(g.get("wind_blockage_index"))
                else None
            ),
        }

    return summary


def neighborhood_comparison(
    cell_id: str, data: dict, radius_m: float = 500,
) -> dict:
    """Hücreyi yakın komşularla karşılaştırır."""
    grid = data["grid"]
    grid_proj = grid.to_crs(CRS_PROJECTED) if grid.crs != CRS_PROJECTED else grid

    target = grid_proj[grid_proj["cell_id"] == cell_id]
    if target.empty:
        return {}
    pt = target.iloc[0].geometry.centroid

    distances = grid_proj.distance(pt)
    neighbors = grid_proj[distances <= radius_m]

    target_score = float(target.iloc[0]["utpm_score"])
    neighbor_mean = float(neighbors["utpm_score"].mean())
    neighbor_median = float(neighbors["utpm_score"].median())

    return {
        "n_neighbors": int(len(neighbors)),
        "radius_m": radius_m,
        "target_utpm": target_score,
        "neighbor_mean_utpm": neighbor_mean,
        "neighbor_median_utpm": neighbor_median,
        "vs_neighborhood": target_score - neighbor_mean,
    }
