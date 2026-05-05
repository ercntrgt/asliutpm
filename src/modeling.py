"""Random Forest eğitimi + 5 katmanlı validation.

Validation katmanları:
1. Klasik 5-fold random CV
2. Mekânsal blok CV (500 m kareler)
3. Hold-out (3 mahalle test'e ayrılır)
4. Permutation null test (target shuffled)
5. Yıllar arası CV (Hafta 11'de: yıl bazlı LST kompozit gerekli)
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold


def prepare_modeling_matrix(
    gdf: gpd.GeoDataFrame,
    features: Iterable[str],
    target: str,
    fillna_zero: bool = True,
    add_saturated_flag: bool = True,
    saturated_col: str = "dtc_breeze_m",
    saturated_threshold: float = 19999,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Feature matrisi + target seri + final feature listesi döner.

    Parameters
    ----------
    gdf : GeoDataFrame
    features : iterable of str
        Bağımsız değişken kolonları.
    target : str
        Hedef kolon (örn. ``"lst_mean"``).
    fillna_zero : bool
        Tüm NaN'ları 0 ile doldur (default True). RF NaN kabul etmediği için zorunlu.
    add_saturated_flag : bool
        ``is_dtc_saturated`` binary kolonunu feature matrisine ekle.
    saturated_col : str
        Saturasyon kontrolü için kolon (default ``"dtc_breeze_m"``).
    saturated_threshold : float
        Bu değerin üstündekiler saturated sayılır.

    Returns
    -------
    X : DataFrame
        Feature matrisi.
    y : Series
        Target.
    feature_names : list of str
        X'in kolonları (saturated flag dahil olabilir).
    """
    df = gdf.copy()

    if add_saturated_flag and saturated_col in df.columns:
        df["is_dtc_saturated"] = (df[saturated_col] >= saturated_threshold).astype(int)

    feat_list = list(features)
    if add_saturated_flag and "is_dtc_saturated" not in feat_list:
        feat_list = feat_list + ["is_dtc_saturated"]

    X = df[feat_list].copy()
    if fillna_zero:
        X = X.fillna(0.0)

    y = df[target].copy()
    if y.isna().any():
        # Target NaN olan satırları drop et
        mask = y.notna()
        X = X.loc[mask]
        y = y.loc[mask]

    return X, y, feat_list


def train_rf(
    X: pd.DataFrame,
    y: pd.Series,
    n_estimators: int = 500,
    random_state: int = 42,
    n_jobs: int = -1,
    **kwargs,
) -> RandomForestRegressor:
    """RF Regressor'u eğitir."""
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=n_jobs,
        **kwargs,
    )
    model.fit(X, y)
    return model


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def random_kfold_cv(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    random_state: int = 42,
    n_estimators: int = 500,
) -> dict:
    """Klasik k-fold random CV.

    Returns
    -------
    dict
        ``fold_metrics`` (list), ``mean`` (dict), ``std`` (dict).
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    fold_metrics = []
    for tr, te in kf.split(X):
        model = train_rf(X.iloc[tr], y.iloc[tr], n_estimators=n_estimators, random_state=random_state)
        pred = model.predict(X.iloc[te])
        fold_metrics.append(_metrics(y.iloc[te].to_numpy(), pred))
    df = pd.DataFrame(fold_metrics)
    return {
        "fold_metrics": fold_metrics,
        "mean": df.mean().round(3).to_dict(),
        "std": df.std().round(3).to_dict(),
    }


def spatial_block_cv(
    X: pd.DataFrame,
    y: pd.Series,
    geometries: gpd.GeoSeries,
    block_size_m: float = 500,
    n_splits: int = 5,
    random_state: int = 42,
    n_estimators: int = 500,
) -> dict:
    """Mekânsal blok CV — 500 m karelere böl, blokları rastgele 5 fold'a ata.

    Mekânsal autocorrelation altında dürüst genelleme metriği.
    """
    centroids = geometries.centroid
    block_x = (centroids.x // block_size_m).astype(int)
    block_y = (centroids.y // block_size_m).astype(int)
    block_id = block_x.astype(str) + "_" + block_y.astype(str)
    unique_blocks = block_id.unique()

    rng = np.random.default_rng(random_state)
    rng.shuffle(unique_blocks)
    block_to_fold = {b: i % n_splits for i, b in enumerate(unique_blocks)}
    fold_assign = block_id.map(block_to_fold).to_numpy()

    fold_metrics = []
    for fold in range(n_splits):
        te_mask = fold_assign == fold
        tr_mask = ~te_mask
        if te_mask.sum() == 0 or tr_mask.sum() == 0:
            continue
        model = train_rf(X.iloc[tr_mask], y.iloc[tr_mask],
                          n_estimators=n_estimators, random_state=random_state)
        pred = model.predict(X.iloc[te_mask])
        fold_metrics.append(_metrics(y.iloc[te_mask].to_numpy(), pred))

    df = pd.DataFrame(fold_metrics)
    return {
        "fold_metrics": fold_metrics,
        "mean": df.mean().round(3).to_dict(),
        "std": df.std().round(3).to_dict(),
        "n_blocks": len(unique_blocks),
        "block_size_m": block_size_m,
    }


def neighborhood_holdout(
    X: pd.DataFrame,
    y: pd.Series,
    neighborhoods: pd.Series,
    test_neighborhoods: Iterable[str],
    n_estimators: int = 500,
    random_state: int = 42,
) -> dict:
    """Belirli mahalleleri tamamen test'e ayır, kalanlarda eğit.

    Mekânsal generalization sınavı: hiç görmediği mahallelerde model nasıl?
    """
    test_neighborhoods = list(test_neighborhoods)
    te_mask = neighborhoods.isin(test_neighborhoods).to_numpy()
    tr_mask = ~te_mask
    model = train_rf(X.iloc[tr_mask], y.iloc[tr_mask],
                      n_estimators=n_estimators, random_state=random_state)
    pred = model.predict(X.iloc[te_mask])
    metrics = _metrics(y.iloc[te_mask].to_numpy(), pred)
    return {
        "metrics": metrics,
        "n_train": int(tr_mask.sum()),
        "n_test": int(te_mask.sum()),
        "test_neighborhoods": test_neighborhoods,
    }


def permutation_null_test(
    X: pd.DataFrame,
    y: pd.Series,
    n_permutations: int = 100,
    n_estimators: int = 200,  # null testte daha az ağaç hızlıdır
    random_state: int = 42,
) -> dict:
    """Target permüte ederek null model dağılımı.

    Gerçek modelin R² skoru null dağılımın 99. percentile'ından
    yüksekse p < 0.01 (anlamlı).
    """
    rng = np.random.default_rng(random_state)
    n = len(y)
    null_r2 = []
    for i in range(n_permutations):
        y_shuffled = y.iloc[rng.permutation(n)].reset_index(drop=True)
        kf = KFold(n_splits=3, shuffle=True, random_state=random_state + i)
        fold_r2 = []
        for tr, te in kf.split(X):
            model = train_rf(X.iloc[tr], y_shuffled.iloc[tr],
                              n_estimators=n_estimators, random_state=random_state)
            pred = model.predict(X.iloc[te])
            fold_r2.append(r2_score(y_shuffled.iloc[te].to_numpy(), pred))
        null_r2.append(float(np.mean(fold_r2)))

    null_r2 = np.array(null_r2)
    return {
        "n_permutations": n_permutations,
        "null_r2_mean": float(null_r2.mean()),
        "null_r2_std": float(null_r2.std()),
        "null_r2_99p": float(np.percentile(null_r2, 99)),
        "null_r2_max": float(null_r2.max()),
        "samples": null_r2.tolist(),
    }


def feature_importance(
    model: RandomForestRegressor,
    X: pd.DataFrame,
    y: pd.Series,
    n_repeats: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Gini + permutation importance birleşik tablo.

    Returns
    -------
    DataFrame
        Kolonlar: ``feature``, ``gini_importance``, ``permutation_importance_mean``,
        ``permutation_importance_std``.
    """
    from sklearn.inspection import permutation_importance

    perm = permutation_importance(
        model, X, y,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=-1,
    )
    return pd.DataFrame({
        "feature": X.columns,
        "gini_importance": model.feature_importances_,
        "permutation_importance_mean": perm.importances_mean,
        "permutation_importance_std": perm.importances_std,
    }).sort_values("permutation_importance_mean", ascending=False).reset_index(drop=True)
