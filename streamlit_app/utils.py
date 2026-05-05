"""Streamlit yardımcıları — veri yükleme, hücre arama, geocoding."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

# Proje paketini import edebilmek için
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DATA_GRID, DATA_PROCESSED,
    UTPM_GPKG, PERSISTENCE_GPKG, GRID_30M_FULL,
    CRS_GEOGRAPHIC, CRS_PROJECTED,
    SELECTED_FEATURES, TARGET_COLUMN,
)


JENKS_LABELS = ["Çok serin", "Serin", "Orta", "Sıcak", "Çok sıcak"]
LISA_DESCRIPTIONS = {
    "HH": "Sıcak küme (UHI çekirdeği) — yüksek LST, yüksek LST'li komşular",
    "LL": "Serin küme — düşük LST, düşük LST'li komşular",
    "HL": "Yerel sıcak anomali — yüksek LST ama serin komşular",
    "LH": "Yerel serin anomali — düşük LST ama sıcak komşular",
    "NS": "İstatistiksel anlamlı küme yok",
}


def load_all_data() -> dict:
    """UTPM, persistence, features ve priority decision layer'ı yükler."""
    from src.config import PRIORITY_GPKG  # geç import — yeni alan

    utpm = gpd.read_file(UTPM_GPKG)
    persist = gpd.read_file(PERSISTENCE_GPKG)
    features = gpd.read_file(GRID_30M_FULL)
    boundary = gpd.read_file(DATA_GRID / "pilot_boundary.gpkg")
    priority = None
    if PRIORITY_GPKG.exists():
        priority = gpd.read_file(PRIORITY_GPKG)
    return {
        "utpm": utpm,
        "persist": persist,
        "features": features,
        "boundary": boundary,
        "priority": priority,
    }


def find_cell_by_coords(
    lat: float, lon: float,
    grid: gpd.GeoDataFrame,
) -> Optional[gpd.GeoSeries]:
    """Verilen lat/lon'a düşen 30m grid hücresini döner.

    Parameters
    ----------
    lat, lon : float
        WGS84 koordinatlar.
    grid : GeoDataFrame
        UTPM grid (EPSG:32636).

    Returns
    -------
    GeoSeries or None
        Hücre satırı (None = pilot dışı).
    """
    pt = gpd.GeoSeries.from_xy([lon], [lat], crs=CRS_GEOGRAPHIC).to_crs(CRS_PROJECTED).iloc[0]
    hits = grid[grid.geometry.contains(pt)]
    if len(hits) == 0:
        # Pilot dışı veya boundary kenar — en yakını dön (max 200 m içinde)
        distances = grid.distance(pt)
        idx = distances.idxmin()
        if distances.loc[idx] > 200:
            return None
        return grid.loc[idx]
    return hits.iloc[0]


def cell_summary(
    cell_id: str,
    data: dict,
) -> dict:
    """Bir hücre için tüm bilgi paketini döner (UTPM + features + persistence)."""
    utpm = data["utpm"]
    features = data["features"]
    persist = data["persist"]

    u = utpm[utpm["cell_id"] == cell_id]
    if u.empty:
        return {}
    u = u.iloc[0]

    f = features[features["cell_id"] == cell_id]
    f = f.iloc[0] if not f.empty else None

    p = persist[persist["cell_id"] == cell_id]
    p = p.iloc[0] if not p.empty else None

    summary = {
        "cell_id": cell_id,
        "lst_mean": float(u[TARGET_COLUMN]) if TARGET_COLUMN in u.index else None,
        "utpm_score": float(u["utpm_score"]),
        "utpm_class": int(u["utpm_class"]),
        "utpm_class_label": JENKS_LABELS[int(u["utpm_class"])] if 0 <= int(u["utpm_class"]) < len(JENKS_LABELS) else "?",
        "lisa_cluster": str(u["lisa_cluster"]),
        "lisa_description": LISA_DESCRIPTIONS.get(str(u["lisa_cluster"]), ""),
        "local_I": float(u["local_I"]),
        "lisa_p": float(u["lisa_p"]),
    }

    if f is not None:
        summary["features"] = {
            col: (float(f[col]) if pd.notna(f[col]) else None)
            for col in SELECTED_FEATURES
            if col in f.index
        }
        # Mahalle bilgisi varsa ekle
        if "mahalle" in f.index and pd.notna(f["mahalle"]):
            summary["mahalle"] = str(f["mahalle"])

    if p is not None:
        summary["persistence"] = {
            "yearly_mean_lst": float(p["lst_yearly_mean"]) if pd.notna(p["lst_yearly_mean"]) else None,
            "yearly_std_lst": float(p["lst_yearly_std"]) if pd.notna(p["lst_yearly_std"]) else None,
            "years_in_top_quartile": int(p["years_in_top_quartile"]) if pd.notna(p["years_in_top_quartile"]) else 0,
            "years_in_bottom_quartile": int(p["years_in_bottom_quartile"]) if pd.notna(p["years_in_bottom_quartile"]) else 0,
        }

    # Priority decision layer
    priority = data.get("priority")
    if priority is not None:
        pr = priority[priority["cell_id"] == cell_id]
        if not pr.empty:
            pr = pr.iloc[0]
            summary["priority"] = {
                "label": str(pr["priority_label"]),
                "wind_blockage_index": float(pr["wind_blockage_index"]) if pd.notna(pr["wind_blockage_index"]) else None,
                "utpm_tier": int(pr["utpm_tier"]) if pd.notna(pr["utpm_tier"]) else None,
                "block_tier": int(pr["block_tier"]) if pd.notna(pr["block_tier"]) else None,
            }

    return summary


def neighborhood_comparison(
    cell_id: str,
    data: dict,
    radius_m: float = 500,
) -> dict:
    """Hücreyi yakın komşularla karşılaştırır (radius_m içindeki grid hücreleri)."""
    utpm = data["utpm"]
    target = utpm[utpm["cell_id"] == cell_id]
    if target.empty:
        return {}
    pt = target.iloc[0].geometry.centroid

    distances = utpm.distance(pt)
    neighbors = utpm[distances <= radius_m]

    target_score = float(target.iloc[0]["utpm_score"])
    neighbor_mean = float(neighbors["utpm_score"].mean())
    neighbor_median = float(neighbors["utpm_score"].median())

    return {
        "n_neighbors": int(len(neighbors)),
        "radius_m": radius_m,
        "target_utpm": target_score,
        "neighbor_mean_utpm": neighbor_mean,
        "neighbor_median_utpm": neighbor_median,
        "vs_neighborhood": target_score - neighbor_mean,  # + = bu hücre komşulardan sıcak
    }
