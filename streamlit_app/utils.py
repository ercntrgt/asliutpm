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


def _empty_summary(cell_id: str = "?") -> dict:
    """Defensive default — tüm key'ler her zaman var olsun ki app.py crash etmesin."""
    return {
        "cell_id": cell_id,
        "lst_mean": None,
        "utpm_score": None,
        "utpm_class": -1,
        "utpm_class_label": "?",
        "lisa_cluster": "NS",
        "lisa_description": LISA_DESCRIPTIONS["NS"],
        "local_I": 0.0,
        "lisa_p": 1.0,
        "features": {},
    }


def cell_summary(cell_id: str, data: dict) -> dict:
    """Bir hücrenin tüm bilgi paketini döner (slim consolidated GPKG'den).

    Defensive: eksik kolon/satır durumunda partial dict yerine tüm key'leri
    olan bir dict döner — app.py'nin hardcoded key access'leri crash etmesin.
    """
    grid = data["grid"]
    g = grid[grid["cell_id"] == cell_id]
    if g.empty:
        return _empty_summary(cell_id)
    g = g.iloc[0]

    summary = _empty_summary(cell_id)
    if pd.notna(g.get(TARGET_COLUMN)):
        summary["lst_mean"] = float(g[TARGET_COLUMN])
    if pd.notna(g.get("utpm_score")):
        summary["utpm_score"] = float(g["utpm_score"])
    if pd.notna(g.get("utpm_class")):
        cls = int(g["utpm_class"])
        summary["utpm_class"] = cls
        if 0 <= cls < len(JENKS_LABELS):
            summary["utpm_class_label"] = JENKS_LABELS[cls]
    cluster = str(g.get("lisa_cluster", "NS")) if pd.notna(g.get("lisa_cluster")) else "NS"
    summary["lisa_cluster"] = cluster
    summary["lisa_description"] = LISA_DESCRIPTIONS.get(cluster, LISA_DESCRIPTIONS["NS"])
    if pd.notna(g.get("local_I")):
        summary["local_I"] = float(g["local_I"])
    if pd.notna(g.get("lisa_p")):
        summary["lisa_p"] = float(g["lisa_p"])

    if "mahalle" in g.index and pd.notna(g["mahalle"]):
        summary["mahalle"] = str(g["mahalle"])

    # Features
    feat_dict = {}
    for col in SELECTED_FEATURES:
        if col in g.index and pd.notna(g[col]):
            feat_dict[col] = float(g[col])
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
    """Hücreyi yakın komşularla karşılaştırır. Defensive — utpm_score eksikse boş döner."""
    grid = data["grid"]
    if "utpm_score" not in grid.columns:
        return {}
    grid_proj = grid.to_crs(CRS_PROJECTED) if grid.crs != CRS_PROJECTED else grid

    target = grid_proj[grid_proj["cell_id"] == cell_id]
    if target.empty or pd.isna(target.iloc[0].get("utpm_score")):
        return {}
    pt = target.iloc[0].geometry.centroid

    distances = grid_proj.distance(pt)
    neighbors = grid_proj[distances <= radius_m]
    valid = neighbors["utpm_score"].dropna()
    if valid.empty:
        return {}

    target_score = float(target.iloc[0]["utpm_score"])
    neighbor_mean = float(valid.mean())
    neighbor_median = float(valid.median())

    return {
        "n_neighbors": int(len(valid)),
        "radius_m": radius_m,
        "target_utpm": target_score,
        "neighbor_mean_utpm": neighbor_mean,
        "neighbor_median_utpm": neighbor_median,
        "vs_neighborhood": target_score - neighbor_mean,
    }
