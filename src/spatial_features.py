"""Mekânsal feature mühendisliği — spatial lag, GWR yardımcıları.

`spatial_lag_lst`: her hücre için k-en-yakın komşu LST ortalaması.
RF'in spatial yapıyı yakalamasını destekler. Hafta 24'te eklendi
(Hafta 23'teki residual Moran I=0.66 sorununu hafifletme amaçlı).

UYARI — data leakage:
Tüm grid'de hesaplandığında train fold'unda test hücrelerinin LST'si
komşu olarak etki edebilir. Behrens & Schmidt (2018) bu yaklaşımı
kabul edilebilir bir trade-off olarak rapor eder. Pure spatial CV için
fold-içi yeniden hesaplanmalı (sonraki çalışma).
"""
from __future__ import annotations

from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd


def spatial_lag_lst(
    grid: gpd.GeoDataFrame,
    lst_col: str = "lst_mean",
    k: int = 8,
    exclude_self: bool = True,
) -> np.ndarray:
    """8-NN komşu LST ortalaması (default exclude_self=True).

    Parameters
    ----------
    grid : GeoDataFrame
        Polygon grid. Centroid kullanılır.
    lst_col : str
        LST kolonu (default ``lst_mean``).
    k : int
        Komşu sayısı (default 8). ``exclude_self=True`` ise tree.query'de
        k+1 alınıp ilk sütun (kendisi) atılır.
    exclude_self : bool
        ``True`` → komşu listesinden hücrenin kendisini hariç tut.

    Returns
    -------
    np.ndarray, shape (n,)
        Her hücre için k-NN komşu LST ortalaması.
    """
    from scipy.spatial import cKDTree

    centroids = np.column_stack([
        grid.geometry.centroid.x.to_numpy(),
        grid.geometry.centroid.y.to_numpy(),
    ])
    tree = cKDTree(centroids)

    n_query = k + 1 if exclude_self else k
    _, idx = tree.query(centroids, k=n_query)
    if exclude_self:
        idx = idx[:, 1:]  # ilk sütun (mesafe=0 = kendisi) at

    lst_values = grid[lst_col].to_numpy(dtype=float)
    # NaN handling: NaN olan komşular nanmean ile geçilsin
    neighbor_lsts = lst_values[idx]   # shape (n, k)
    return np.nanmean(neighbor_lsts, axis=1)


def spatial_lag_generic(
    grid: gpd.GeoDataFrame,
    value_col: str,
    k: int = 8,
    exclude_self: bool = True,
    weights: Optional[str] = None,
) -> np.ndarray:
    """Spatial lag jenerik — herhangi bir kolon için k-NN ortalama.

    Parameters
    ----------
    weights : {None, "inverse_distance"}
        ``None`` → eşit ağırlık, ``inverse_distance`` → 1/d ağırlık.
    """
    from scipy.spatial import cKDTree

    centroids = np.column_stack([
        grid.geometry.centroid.x.to_numpy(),
        grid.geometry.centroid.y.to_numpy(),
    ])
    tree = cKDTree(centroids)

    n_query = k + 1 if exclude_self else k
    distances, idx = tree.query(centroids, k=n_query)

    if exclude_self:
        idx = idx[:, 1:]
        distances = distances[:, 1:]

    values = grid[value_col].to_numpy(dtype=float)
    neighbor_vals = values[idx]

    if weights == "inverse_distance":
        # Eps ekle 0 bölmesini önle
        w = 1.0 / (distances + 1e-6)
        w_sum = w.sum(axis=1, keepdims=True)
        return np.nansum(neighbor_vals * w, axis=1) / w_sum.squeeze()
    return np.nanmean(neighbor_vals, axis=1)
