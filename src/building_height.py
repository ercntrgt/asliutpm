"""Bina yüksekliği: kat→metre dönüşümü, buffer cascade imputation, grid agregasyonu.

İmar verisinde ~%33 kat verisi eksik. Bu modül:
1. Kat sayısını metreye çevirir (TS 9111: konut 3.0 m).
2. Eksik kayıtları, çevresindeki bilinen komşuların ortalamasıyla doldurur
   (buffer cascade: 10 → 100 → 500 → 1000 m, en küçük buffer'da
   ``min_neighbors`` komşu bulunan).
3. Imputation kalitesini 5-fold CV ile ölçer (RMSE, MAE, R²).
4. Bina noktalarını 30 m grid'e ortalama yükseklik + yoğunluk olarak bağlar.
"""
from __future__ import annotations

from typing import Iterable, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def floors_to_height(
    floors: pd.Series | np.ndarray,
    floor_height_m: float = 3.0,
) -> np.ndarray:
    """Kat sayısını metreye çevirir.

    Parameters
    ----------
    floors : pd.Series or array
        Kat sayısı. ``NaN`` olan değerler ``NaN`` döner.
    floor_height_m : float
        Kat başına yükseklik. Default 3.0 (TS 9111 konut).

    Returns
    -------
    np.ndarray
        Metre cinsinden bina yüksekliği. Aynı uzunlukta.
    """
    arr = np.asarray(floors, dtype=float)
    return arr * floor_height_m


def buffer_cascade_impute(
    known: gpd.GeoDataFrame,
    unknown: gpd.GeoDataFrame,
    height_col: str,
    buffers_m: Iterable[float] = (10, 100, 500, 1000),
    min_neighbors: int = 3,
    fallback_value: Optional[float] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Her unknown nokta için en küçük buffer'da yeterli komşu bulup ortalama al.

    Tek seferlik cKDTree query — N×M değil, query başına ortalama O(log N)
    + komşu sayısı. 28K nokta için saniyeler içinde biter.

    Parameters
    ----------
    known : GeoDataFrame
        Yüksekliği bilinen noktalar. ``height_col`` kolonu olmalı.
        CRS projeli olmalı (mesafeler metre cinsinden).
    unknown : GeoDataFrame
        Yüksekliği eksik noktalar.
    height_col : str
        Bilinen yükseklik kolonu adı (örn. ``"height_m"``).
    buffers_m : iterable of float
        Cascade buffer yarıçapları (artan sırada). Default (10,100,500,1000).
    min_neighbors : int
        Minimum komşu sayısı. Bu sayıya ulaşılan en küçük buffer kullanılır.
    fallback_value : float, optional
        En büyük buffer'da bile komşu yoksa atanan değer.
        ``None`` ise known'ın global medyanı.

    Returns
    -------
    imputed : np.ndarray, shape (n_unknown,)
        Tahmin edilen yükseklik (metre).
    used_buffer : np.ndarray, shape (n_unknown,)
        Her tahminde kullanılan buffer (m). Fallback için ``-1``.
    """
    if known.crs is None or known.crs.is_geographic:
        raise ValueError(
            f"known projeli CRS olmalı (örn. EPSG:32636), aldım: {known.crs}"
        )
    if known.crs != unknown.crs:
        raise ValueError(f"CRS uyumsuz: known={known.crs}, unknown={unknown.crs}")

    buffers_m = tuple(sorted(buffers_m))

    # Known koordinatlar + ağaç
    known_xy = np.column_stack([
        known.geometry.x.to_numpy(),
        known.geometry.y.to_numpy(),
    ])
    known_h = known[height_col].to_numpy(dtype=float)

    if fallback_value is None:
        fallback_value = float(np.nanmedian(known_h))

    tree = cKDTree(known_xy)

    unknown_xy = np.column_stack([
        unknown.geometry.x.to_numpy(),
        unknown.geometry.y.to_numpy(),
    ])

    n = len(unknown_xy)
    imputed = np.full(n, np.nan)
    used_buffer = np.full(n, -1, dtype=int)

    # Tüm buffer'ları tek loop'ta dene
    for i in range(n):
        for buf in buffers_m:
            idx = tree.query_ball_point(unknown_xy[i], buf)
            if len(idx) >= min_neighbors:
                imputed[i] = float(np.nanmean(known_h[idx]))
                used_buffer[i] = int(buf)
                break
        else:
            imputed[i] = fallback_value

    return imputed, used_buffer


def cv_imputation(
    known: gpd.GeoDataFrame,
    height_col: str,
    buffers_m: Iterable[float] = (10, 100, 500, 1000),
    min_neighbors: int = 3,
    n_splits: int = 5,
    random_state: int = 42,
) -> dict:
    """5-fold cross-validation ile imputation kalitesini ölçer.

    Her fold'da test set'in gerçek değerleri "bilinmiyormuş" gibi davranılır,
    diğer 4 fold known kullanılarak buffer cascade ile tahmin edilir.

    Returns
    -------
    dict
        ``actuals``, ``predicted``, ``rmse``, ``mae``, ``r2``,
        ``buffer_distribution`` (kullanılan buffer'ların histogram'ı).
    """
    from sklearn.model_selection import KFold
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    actuals, preds, used_buffers_all = [], [], []

    for train_idx, test_idx in kf.split(known):
        train = known.iloc[train_idx]
        test = known.iloc[test_idx]
        pred, used = buffer_cascade_impute(
            train, test, height_col,
            buffers_m=buffers_m,
            min_neighbors=min_neighbors,
        )
        actuals.append(test[height_col].to_numpy(dtype=float))
        preds.append(pred)
        used_buffers_all.append(used)

    actuals = np.concatenate(actuals)
    preds = np.concatenate(preds)
    used_buffers_all = np.concatenate(used_buffers_all)

    rmse = float(np.sqrt(mean_squared_error(actuals, preds)))
    mae = float(mean_absolute_error(actuals, preds))
    r2 = float(r2_score(actuals, preds))

    buffer_dist = pd.Series(used_buffers_all).value_counts().sort_index().to_dict()

    return {
        "actuals": actuals,
        "predicted": preds,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "buffer_distribution": buffer_dist,
        "n_total": len(actuals),
    }


def building_metrics_per_cell(
    buildings: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    height_col: str,
    cell_id_col: str = "cell_id",
) -> gpd.GeoDataFrame:
    """30 m grid hücrelerine bina sayısı, ortalama yükseklik, yoğunluk ekler.

    Parameters
    ----------
    buildings : GeoDataFrame
        Tüm bina noktaları (known + imputed). ``height_col`` kolonu olmalı.
    grid : GeoDataFrame
        30 m grid (``cell_id`` ve ``geometry``).
    height_col : str
        Yükseklik kolonu (genelde ``"height_m"``).
    cell_id_col : str
        Grid'deki cell id kolonu adı.

    Returns
    -------
    GeoDataFrame
        Grid + 3 yeni kolon:
        - ``building_count`` : hücredeki bina sayısı
        - ``building_height_mean`` : ortalama yükseklik (m)
        - ``building_density_per_km2`` : bina sayısı / km²
        Hücrede bina yoksa count=0, height=NaN, density=0.
    """
    if buildings.crs != grid.crs:
        raise ValueError(f"CRS uyumsuz: buildings={buildings.crs}, grid={grid.crs}")

    # Sjoin: bina noktalarını hücrelerle eşleştir
    joined = gpd.sjoin(
        buildings[["geometry", height_col]],
        grid[[cell_id_col, "geometry"]],
        how="inner",
        predicate="within",
    )

    agg = (
        joined.groupby(cell_id_col)
        .agg(
            building_count=(height_col, "count"),
            building_height_mean=(height_col, "mean"),
        )
        .reset_index()
    )

    out = grid.merge(agg, on=cell_id_col, how="left")

    cell_area_m2 = grid.geometry.iloc[0].area
    out["building_count"] = out["building_count"].fillna(0).astype(int)
    out["building_density_per_km2"] = (
        out["building_count"] * 1e6 / cell_area_m2
    ).round(1)

    return out
