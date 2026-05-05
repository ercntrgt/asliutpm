"""Rüzgar-yönelimli kıyı mesafesi (DTC_breeze) ve OSM yol yoğunluğu.

DTC_breeze: her grid hücresinden, hakim rüzgar yönüne (~165° SSE) doğru bir
ışın gönderilir; ışının kıyı çizgisini ilk kestiği noktaya olan mesafe.
Mantık: rüzgar 165°'den geliyor → o yönde ray çekersen rüzgarın geldiği denize
doğru gitmiş olursun → kesişim, denizden esintinin bu hücreye gelmek için
kat etmesi gereken kara mesafesinin tersi (kara mesafesi = ray uzunluğu).

Yol yoğunluğu: OSM araç yol ağı, hücre içi toplam yol uzunluğu.
"""
from __future__ import annotations

from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union


# =============================================================================
# Coastline + ray casting
# =============================================================================

def load_osm_coastline(
    boundary: gpd.GeoDataFrame,
    buffer_m: float = 5000,
) -> gpd.GeoDataFrame:
    """OSM'den ``natural=coastline`` çek, projeli CRS'e döndür.

    Pilot sınırın etrafına ``buffer_m`` ekleyip o alanı sorgular. Konyaaltı
    için coastline tek-line. Geniş bir alanda olabilir.

    Returns
    -------
    GeoDataFrame
        LineString geometriler. Pilot CRS'inde.
    """
    import osmnx as ox

    target_crs = boundary.crs
    bnd_buffered = boundary.to_crs(target_crs).buffer(buffer_m).to_crs("EPSG:4326")
    poly_4326 = unary_union(bnd_buffered.geometry.values)

    coast = ox.features_from_polygon(poly_4326, tags={"natural": "coastline"})
    if coast.empty:
        raise RuntimeError(
            "OSM'de coastline bulunamadı. Buffer artırın veya elle bir LineString sağlayın."
        )

    # Sadece çizgi/poligon kenarları al
    coast = coast[coast.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    return coast.to_crs(target_crs)


def _cast_ray(point: Point, angle_deg: float, length_m: float) -> LineString:
    """Pusula açısında (0=N, 90=E) ray üretir.

    Parameters
    ----------
    point : shapely.Point
    angle_deg : float
        Pusula açısı (0=Kuzey, 90=Doğu, 180=Güney, 270=Batı).
    length_m : float
        Ray uzunluğu (metre).

    Returns
    -------
    LineString
    """
    rad = np.radians(angle_deg)
    dx = np.sin(rad) * length_m   # Doğu yönü
    dy = np.cos(rad) * length_m   # Kuzey yönü
    return LineString([(point.x, point.y), (point.x + dx, point.y + dy)])


def _ray_distance_to_line(
    origin: Point,
    angle_deg: float,
    target: object,
    max_dist_m: float,
) -> float:
    """``origin``'den ``angle_deg`` yönüne ray ile ``target``'a en yakın kesişim mesafesi.

    Returns
    -------
    float
        Metre. Kesişim yoksa ``max_dist_m``.
    """
    ray = _cast_ray(origin, angle_deg, max_dist_m)
    inter = ray.intersection(target)
    if inter.is_empty:
        return float(max_dist_m)

    # Çok parça olabilir; en yakın noktayı bul
    if hasattr(inter, "geoms"):
        d = min(origin.distance(g) for g in inter.geoms)
    else:
        d = origin.distance(inter)
    return float(d)


def dtc_breeze_for_geometries(
    geometries: pd.Series | gpd.GeoSeries,
    coastline: gpd.GeoDataFrame,
    wind_from_deg: float = 165,
    max_dist_m: float = 20000,
) -> np.ndarray:
    """Her geometri için ray casting ile rüzgar-yönelimli kıyı mesafesi.

    Geometriler poligon ise centroid kullanılır.

    Parameters
    ----------
    geometries : GeoSeries
        Hücre poligonları veya noktalar.
    coastline : GeoDataFrame
        OSM coastline.
    wind_from_deg : float
        Hakim rüzgar **kaynak** yönü (0=N, 165=SSE). Default 165 (Antalya yaz).
    max_dist_m : float
        Maksimum ray uzunluğu (metre). Bunun ötesinde kıyı bulunamazsa
        bu değer döner — tezde "saturation" olarak yorumlanır.

    Returns
    -------
    np.ndarray, shape (n,)
        Her hücre için DTC_breeze (m).
    """
    coast_geom = unary_union(coastline.geometry.values)

    centroids = geometries.centroid if geometries.iloc[0].geom_type != "Point" else geometries
    out = np.full(len(centroids), np.nan)
    for i, p in enumerate(centroids.values):
        out[i] = _ray_distance_to_line(p, wind_from_deg, coast_geom, max_dist_m)
    return out


# =============================================================================
# OSM yol yoğunluğu
# =============================================================================

def load_osm_roads(
    boundary: gpd.GeoDataFrame,
    network_type: str = "drive",
    buffer_m: float = 500,
) -> gpd.GeoDataFrame:
    """OSM araç yol ağını çeker (LineString GeoDataFrame).

    Pilot sınırın etrafına küçük bir buffer ekleyip yol kesintilerini önler.

    Parameters
    ----------
    boundary : GeoDataFrame
    network_type : str
        ``"drive"``, ``"all"``, ``"walk"`` vb. Default ``"drive"``
        (yaya/bisiklet yolları termal için ayrı; default sadece araç).
    buffer_m : float
        Sınır etrafı buffer (metre).

    Returns
    -------
    GeoDataFrame
        Yollar (LineString), projeli CRS'te.
    """
    import osmnx as ox

    target_crs = boundary.crs
    bnd_buffered = boundary.to_crs(target_crs).buffer(buffer_m).to_crs("EPSG:4326")
    poly_4326 = unary_union(bnd_buffered.geometry.values)

    G = ox.graph_from_polygon(poly_4326, network_type=network_type, simplify=True)
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    return edges.to_crs(target_crs)


def road_length_per_cell(
    roads: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    cell_id_col: str = "cell_id",
) -> gpd.GeoDataFrame:
    """30 m grid hücreleriyle yolları kes, hücre başına toplam yol uzunluğunu hesapla.

    Returns
    -------
    GeoDataFrame
        Grid + iki yeni kolon:
        - ``road_length_m`` — hücre içi toplam yol uzunluğu (metre)
        - ``road_density_m_per_km2`` — yoğunluk (m / km²)
    """
    if roads.crs != grid.crs:
        raise ValueError(f"CRS uyumsuz: roads={roads.crs}, grid={grid.crs}")

    # Yolları hücrelerle kes (overlay) ve uzunluk al
    roads_lite = roads[["geometry"]].copy()
    grid_lite = grid[[cell_id_col, "geometry"]].copy()

    # overlay intersection: her grid hücresi × her yol parçası kesişimi
    inter = gpd.overlay(roads_lite, grid_lite, how="intersection", keep_geom_type=False)
    inter = inter[inter.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    inter["seg_len_m"] = inter.geometry.length

    by_cell = inter.groupby(cell_id_col)["seg_len_m"].sum().reset_index(
        name="road_length_m"
    )

    out = grid.merge(by_cell, on=cell_id_col, how="left")
    out["road_length_m"] = out["road_length_m"].fillna(0.0)

    cell_area_m2 = grid.geometry.iloc[0].area
    out["road_density_m_per_km2"] = (
        out["road_length_m"] * 1e6 / cell_area_m2
    ).round(1)
    return out
