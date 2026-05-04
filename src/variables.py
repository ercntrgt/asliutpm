"""Bağımsız değişkenlerin grid agregasyonu.

Raster değişkenler (LST, NDVI, Albedo, geçirimsiz yüzey) zonal statistics
ile 30 m grid'e bağlanır. Vektör değişkenler (yapı yoğunluğu, yol yoğunluğu)
spatial join ile.

İlk hafta: ``zonal_stats_to_grid`` (raster → grid).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import geopandas as gpd
import numpy as np
import pandas as pd


def zonal_stats_to_grid(
    grid: gpd.GeoDataFrame,
    raster_path: str | Path,
    stats: Iterable[str] = ("mean", "median", "std", "count"),
    prefix: str = "",
    nodata: Optional[float] = None,
    all_touched: bool = False,
) -> gpd.GeoDataFrame:
    """Grid hücreleri üzerinden raster zonal statistics hesaplar.

    Parameters
    ----------
    grid : GeoDataFrame
        Polygon grid (örn. 30m). Raster ile aynı CRS olmak ZORUNDA değil
        — fonksiyon raster CRS'ine reproject eder.
    raster_path : str or Path
        Tek-bantlı raster dosyası (GeoTIFF).
    stats : iterable of str
        rasterstats.zonal_stats stat'ları. Default: mean, median, std, count.
    prefix : str
        Sütun adlarına ön ek (örn. ``"lst_"`` → ``lst_mean``, ``lst_median``).
    nodata : float, optional
        Raster'da nodata değeri (None ise raster header'dan alınır).
    all_touched : bool
        True ise hücreye dokunan tüm pikseller, False ise sadece centroid'i
        içerenler. Default False (daha sıkı).

    Returns
    -------
    GeoDataFrame
        Orijinal grid + her stat için yeni kolon. CRS değişmez (grid'in CRS'i).
    """
    from rasterio import open as rio_open
    from rasterstats import zonal_stats

    raster_path = Path(raster_path)
    if not raster_path.exists():
        raise FileNotFoundError(f"Raster yok: {raster_path}")

    with rio_open(raster_path) as src:
        raster_crs = src.crs

    # Grid'i raster CRS'ine reproject et (zonal_stats için gerekli)
    if grid.crs != raster_crs:
        grid_for_stats = grid.to_crs(raster_crs)
    else:
        grid_for_stats = grid

    results = zonal_stats(
        vectors=grid_for_stats.geometry,
        raster=str(raster_path),
        stats=list(stats),
        nodata=nodata,
        all_touched=all_touched,
        geojson_out=False,
    )

    stats_df = pd.DataFrame(results)
    if prefix:
        stats_df.columns = [f"{prefix}{c}" for c in stats_df.columns]

    out = grid.copy().reset_index(drop=True)
    stats_df = stats_df.reset_index(drop=True)
    for c in stats_df.columns:
        out[c] = stats_df[c]
    return out
