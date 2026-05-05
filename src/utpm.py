"""UTPM (Urban Thermal Persistence Model) — lineer indeks + mekânsal analiz.

UTPM iş akışı:
1. RF/SHAP'ten **importance ağırlıkları** çıkar
2. **Z-skor** standardize edilmiş feature'lara ağırlıklı toplam ⇒ UTPM skoru
3. **Moran's I** ile mekânsal otokorelasyonu test et (kümeli mi?)
4. **LISA** (Local Moran's I) ile her hücreye cluster tipi ata (HH, LL, HL, LH)
5. **Jenks natural breaks** ile 5 sınıf kategori (karar destek)
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.ensemble import RandomForestRegressor


# =============================================================================
# SHAP analizi
# =============================================================================

def shap_tree_explainer(
    model: RandomForestRegressor,
    X: pd.DataFrame,
    sample_n: int = 1000,
    approximate: bool = True,
):
    """RF için SHAP TreeExplainer — sample + approximate modu hızlandırır.

    Parameters
    ----------
    model : trained RandomForestRegressor
    X : DataFrame
        Feature matrisi.
    sample_n : int
        SHAP'ı hesaplamak için örneklem boyutu (28K hücrede full hesap çok yavaş).
        Default 1000 — global importance için yeterli.
    approximate : bool
        ``shap_values(approximate=True)`` — 10x hızlanma, hafif accuracy kaybı.
        Global importance ve beeswarm için pratikte fark görünmez.

    Returns
    -------
    sample_X : DataFrame
    shap_values : np.ndarray
        Shape (sample_n, n_features).
    explainer : shap.TreeExplainer
    """
    import shap

    if sample_n is not None and sample_n < len(X):
        sample_X = X.sample(sample_n, random_state=42).reset_index(drop=True)
    else:
        sample_X = X.reset_index(drop=True)

    # feature_perturbation="tree_path_dependent" — RF için hızlı + uyumlu
    explainer = shap.TreeExplainer(
        model,
        feature_perturbation="tree_path_dependent",
    )
    shap_values = explainer.shap_values(
        sample_X,
        check_additivity=False,
        approximate=approximate,
    )
    return sample_X, shap_values, explainer


def shap_global_importance(shap_values: np.ndarray, feature_names: list) -> pd.DataFrame:
    """Global SHAP feature importance — mean(|SHAP|).

    Returns
    -------
    DataFrame
        Kolonlar: ``feature``, ``shap_mean_abs``, ``shap_normalized`` (sum=1).
    """
    imp = np.abs(shap_values).mean(axis=0)
    df = pd.DataFrame({
        "feature": feature_names,
        "shap_mean_abs": imp,
    }).sort_values("shap_mean_abs", ascending=False).reset_index(drop=True)
    df["shap_normalized"] = df["shap_mean_abs"] / df["shap_mean_abs"].sum()
    return df


# =============================================================================
# UTPM lineer indeks
# =============================================================================

def compute_utpm_index(
    df: pd.DataFrame,
    z_features: Iterable[str],
    weights: Iterable[float],
    sign_flips: Optional[dict] = None,
) -> np.ndarray:
    """Ağırlıklı z-skor toplamı = UTPM ham skor.

    Parameters
    ----------
    df : DataFrame
        Z-skorlu kolonları içeren tablo.
    z_features : iterable of str
        Z-skor feature kolonları (örn. ``["albedo_mean_z", ...]``).
    weights : iterable of float
        Her feature için ağırlık (normalize edilmiş, sum=1 olmak zorunda değil).
    sign_flips : dict, optional
        Bazı feature'lar için yön çevir (örn. NDVI yüksekse serin → çevir).
        Format: ``{"ndvi_mean_z": -1, ...}``. Yoksa hepsi +1.

    Returns
    -------
    np.ndarray
        UTPM skoru (her hücre için).
    """
    z_features = list(z_features)
    weights = np.asarray(list(weights), dtype=float)
    sign_flips = sign_flips or {}

    score = np.zeros(len(df), dtype=float)
    for feat, w in zip(z_features, weights):
        sign = sign_flips.get(feat, 1.0)
        score = score + sign * w * df[feat].fillna(0).to_numpy()
    return score


def normalize_utpm(score: np.ndarray, method: str = "minmax") -> np.ndarray:
    """UTPM ham skoru 0-1 veya 0-100'e normalize eder.

    Parameters
    ----------
    method : {"minmax", "rank"}
        ``minmax`` lineer (min=0, max=1); ``rank`` percentile-based (uniform 0-1).
    """
    score = np.asarray(score, dtype=float)
    if method == "minmax":
        s_min, s_max = np.nanmin(score), np.nanmax(score)
        return (score - s_min) / (s_max - s_min) if s_max > s_min else np.zeros_like(score)
    elif method == "rank":
        ranks = pd.Series(score).rank(pct=True).to_numpy()
        return ranks
    raise ValueError(f"Bilinmeyen method: {method!r}")


# =============================================================================
# Mekânsal otokorelasyon (Moran's I + LISA)
# =============================================================================

def compute_moran_i(
    values: np.ndarray,
    geometries: gpd.GeoSeries,
    k_neighbors: int = 8,
) -> dict:
    """Global Moran's I.

    Parameters
    ----------
    values : array-like
        Test edilecek değer (örn. UTPM skoru, LST, residual).
    geometries : GeoSeries
        Aynı uzunlukta poligon/nokta geometrileri (centroid kullanılır).
    k_neighbors : int
        K-en-yakın komşu sayısı (W matrisi için). Default 8.

    Returns
    -------
    dict
        ``I``, ``expected_I``, ``z_score``, ``p_value`` (one-sided).
    """
    from libpysal.weights import KNN

    centroids = np.column_stack([
        geometries.centroid.x.to_numpy(),
        geometries.centroid.y.to_numpy(),
    ])
    w = KNN.from_array(centroids, k=k_neighbors)
    w.transform = "r"  # row-standardize

    values = np.asarray(values, dtype=float)
    mask = np.isfinite(values)
    if not mask.all():
        # libpysal NaN sevmiyor; NaN'ları drop et
        valid_idx = np.where(mask)[0]
        sub_centroids = centroids[valid_idx]
        sub_w = KNN.from_array(sub_centroids, k=k_neighbors)
        sub_w.transform = "r"
        values = values[mask]
        w = sub_w

    from esda.moran import Moran
    mi = Moran(values, w, permutations=99)
    return {
        "I": float(mi.I),
        "expected_I": float(mi.EI),
        "z_score": float(mi.z_norm),
        "p_value": float(mi.p_norm),
        "p_sim": float(mi.p_sim),
    }


def compute_local_moran(
    values: np.ndarray,
    geometries: gpd.GeoSeries,
    k_neighbors: int = 8,
    seed: int = 42,
) -> pd.DataFrame:
    """Local Moran's I (LISA) — her hücre için cluster tipi.

    Returns
    -------
    DataFrame
        Kolonlar: ``Is`` (local I), ``q`` (1=HH, 2=LH, 3=LL, 4=HL),
        ``p_sim`` (permütasyon p), ``cluster_label`` (string).
    """
    from libpysal.weights import KNN
    from esda.moran import Moran_Local

    centroids = np.column_stack([
        geometries.centroid.x.to_numpy(),
        geometries.centroid.y.to_numpy(),
    ])
    w = KNN.from_array(centroids, k=k_neighbors)
    w.transform = "r"

    values = np.asarray(values, dtype=float)
    values = np.nan_to_num(values, nan=np.nanmedian(values))

    lm = Moran_Local(values, w, permutations=99, seed=seed)

    # Cluster etiketleri (sadece anlamlı olanlar; p<0.05)
    sig = lm.p_sim < 0.05
    labels = np.array(["NS"] * len(values), dtype=object)  # NS = not significant
    quad_to_label = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    for i in range(len(values)):
        if sig[i]:
            labels[i] = quad_to_label.get(int(lm.q[i]), "NS")

    return pd.DataFrame({
        "Is": lm.Is,
        "q": lm.q,
        "p_sim": lm.p_sim,
        "cluster_label": labels,
    })


# =============================================================================
# Jenks sınıflama
# =============================================================================

def jenks_classify(
    values: np.ndarray,
    k: int = 5,
    labels: Optional[list[str]] = None,
) -> tuple[np.ndarray, list[float]]:
    """Jenks natural breaks ile k sınıfa ayır.

    Returns
    -------
    classes : np.ndarray of int
        Sınıf indeksleri (0..k-1).
    bins : list of float
        k+1 sınır değer.
    """
    from mapclassify import NaturalBreaks

    values = np.asarray(values, dtype=float)
    mask = np.isfinite(values)
    if mask.sum() == 0:
        return np.full(len(values), -1, dtype=int), []

    nb = NaturalBreaks(values[mask], k=k)
    bins = [float(values[mask].min())] + [float(b) for b in nb.bins]

    classes = np.full(len(values), -1, dtype=int)
    classes[mask] = nb.yb
    return classes, bins
