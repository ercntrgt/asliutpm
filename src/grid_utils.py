"""30 m + 100 m grid sistemi.

Pilot alan sınırını noktalardan üretir, üzerine analitik (30 m) ve
planlama (100 m) gridleri kurar; her 30 m hücreye 100 m parent atar.

Tüm fonksiyonlar projeli CRS (EPSG:32636) bekler.
"""
from __future__ import annotations

import math
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import concave_hull
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def build_pilot_boundary(
    points: gpd.GeoDataFrame,
    group_col: str = "mahalle",
    ratio: float = 0.3,
    buffer_m: float = 50.0,
    min_points_for_hull: int = 4,
) -> gpd.GeoDataFrame:
    """Nokta verisinden mahalle bazlı concave hull birleştirip pilot sınır üretir.

    Her mahalle için ayrı concave hull alınır (ratio düşük ⇒ daha sıkı sınır).
    Az noktalı mahalleler convex hull + buffer fallback'iyle ele alınır.
    Sonunda hepsi birleştirilip ufak bir buffer eklenir (kenara taşmış
    noktaları kapsamak için).

    Parameters
    ----------
    points : GeoDataFrame
        Pilot mahallelerin imar noktaları. CRS projeli olmalı.
    group_col : str
        Mahalle adı kolonu.
    ratio : float
        ``shapely.concave_hull`` ratio parametresi (0..1). Düşük = sıkı.
    buffer_m : float
        Final union'a uygulanacak buffer (metre).
    min_points_for_hull : int
        Bu sayıdan az noktası olan mahalleler convex hull fallback kullanır.

    Returns
    -------
    GeoDataFrame
        Tek satırlı GeoDataFrame, geometri = pilot sınır (MultiPolygon olabilir).
    """
    if points.crs is None or points.crs.is_geographic:
        raise ValueError(
            f"Projeli CRS bekleniyor (örn. EPSG:32636), aldığım: {points.crs}"
        )

    polys = []
    for mahalle, sub in points.groupby(group_col):
        if len(sub) < min_points_for_hull:
            poly = sub.geometry.unary_union.convex_hull.buffer(buffer_m)
        else:
            mp = sub.geometry.unary_union  # MultiPoint
            try:
                poly = concave_hull(mp, ratio=ratio)
                if poly.is_empty or not poly.is_valid:
                    poly = mp.convex_hull
            except Exception:
                poly = mp.convex_hull
        polys.append(poly)

    merged = unary_union(polys).buffer(buffer_m)

    return gpd.GeoDataFrame(
        {"name": ["pilot_boundary"]},
        geometry=[merged],
        crs=points.crs,
    )


def _aligned_origin(value: float, cell_size: float) -> float:
    """``value``'yu ``cell_size``'ın aşağı katına yuvarlar."""
    return math.floor(value / cell_size) * cell_size


def make_grid(
    boundary: gpd.GeoDataFrame,
    cell_size_m: float,
    id_prefix: str,
    origin: Optional[tuple[float, float]] = None,
) -> gpd.GeoDataFrame:
    """Sınırın bbox'ını kapsayan kare grid üretir.

    ``origin`` verilmezse bbox'ın sol-altı ``cell_size_m``'in katına
    yuvarlanarak kullanılır. İki grid'i hizalı tutmak için 30 m ve
    100 m grid'lerini **aynı origin** ile çağırın.

    Parameters
    ----------
    boundary : GeoDataFrame
        Pilot sınır (üretilen grid bbox'ından kırpılmaz, sadece bbox referansı).
    cell_size_m : float
        Hücre boyutu (metre).
    id_prefix : str
        Hücre id formatı: ``f"{prefix}_{i:04d}_{j:04d}"``. Önerilen: "30m", "100m".
    origin : tuple of (float, float), optional
        ``(min_x, min_y)`` — yoksa bbox'tan türetilir.

    Returns
    -------
    GeoDataFrame
        Kolonlar: ``cell_id``, ``i`` (sütun idx), ``j`` (satır idx),
        ``geometry`` (Polygon). CRS sınırın CRS'i.
    """
    minx, miny, maxx, maxy = boundary.total_bounds

    if origin is None:
        ox = _aligned_origin(minx, cell_size_m)
        oy = _aligned_origin(miny, cell_size_m)
    else:
        ox, oy = origin

    nx = math.ceil((maxx - ox) / cell_size_m)
    ny = math.ceil((maxy - oy) / cell_size_m)

    cells = []
    ids: list[str] = []
    is_idx: list[int] = []
    js_idx: list[int] = []
    for j in range(ny):
        for i in range(nx):
            x0 = ox + i * cell_size_m
            y0 = oy + j * cell_size_m
            cells.append(box(x0, y0, x0 + cell_size_m, y0 + cell_size_m))
            ids.append(f"{id_prefix}_{i:04d}_{j:04d}")
            is_idx.append(i)
            js_idx.append(j)

    return gpd.GeoDataFrame(
        {"cell_id": ids, "i": is_idx, "j": js_idx},
        geometry=cells,
        crs=boundary.crs,
    )


def clip_grid_to_boundary(
    grid: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    method: str = "centroid",
) -> gpd.GeoDataFrame:
    """Sınır dışındaki hücreleri eler.

    Parameters
    ----------
    grid : GeoDataFrame
        ``make_grid`` çıktısı.
    boundary : GeoDataFrame
        Pilot sınır (tek geometriye union'lanır).
    method : {"centroid", "intersects", "within"}
        - ``centroid``: hücrenin centroid'i sınır içinde mi (default, fast).
        - ``intersects``: hücrenin herhangi bir kısmı sınırla kesişiyor mu (geniş).
        - ``within``: hücre tamamen sınır içinde mi (konservatif).
    """
    bnd = unary_union(boundary.geometry.values)

    if method == "centroid":
        mask = grid.geometry.centroid.intersects(bnd)
    elif method == "intersects":
        mask = grid.geometry.intersects(bnd)
    elif method == "within":
        mask = grid.geometry.within(bnd)
    else:
        raise ValueError(f"Bilinmeyen method: {method!r}")

    return grid[mask].reset_index(drop=True)


def assign_parent(
    child: gpd.GeoDataFrame,
    parent: gpd.GeoDataFrame,
    parent_id_col: str = "cell_id",
    out_col: str = "parent_id",
) -> gpd.GeoDataFrame:
    """30 m hücreye centroid spatial join ile 100 m parent_id ekler.

    Parameters
    ----------
    child : GeoDataFrame
        30 m grid (cell_id, geometry).
    parent : GeoDataFrame
        100 m grid (cell_id, geometry).
    parent_id_col : str
        Parent grid'inde id kolonunun adı.
    out_col : str
        Çıktıdaki yeni kolon adı.

    Returns
    -------
    GeoDataFrame
        ``child``'ın aynısı + ``out_col`` (string, parent yoksa NaN).
    """
    if child.crs != parent.crs:
        raise ValueError(f"CRS uyumsuz: child={child.crs}, parent={parent.crs}")

    centroids = child[["cell_id"]].copy()
    centroids["geometry"] = child.geometry.centroid
    centroids = gpd.GeoDataFrame(centroids, geometry="geometry", crs=child.crs)

    # parent_id_col çakışmasın diye yeniden adlandırarak gönder
    parent_renamed = parent[[parent_id_col, "geometry"]].rename(
        columns={parent_id_col: "_parent_id_tmp"}
    )

    joined = gpd.sjoin(
        centroids,
        parent_renamed,
        how="left",
        predicate="within",
    )

    # Bir centroid birden çok parent'a denk gelirse (sınırda) ilk eşleşmeyi al
    parent_map = (
        joined.groupby("cell_id")["_parent_id_tmp"].first().to_dict()
    )

    out = child.copy()
    out[out_col] = out["cell_id"].map(parent_map)
    return out
