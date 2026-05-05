"""Z-skor + log dönüşümleri.

Skewed (genelde yoğunluk türü) değişkenlere log1p, sonra hepsine z-skor
uygulanır. Sonuç: tüm değişkenler mean=0, std=1, karşılaştırılabilir
ölçek. RandomForest gerektirmez ama interpretability ve gelecek
lineer modeller için faydalı.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd


def compute_skewness(df: pd.DataFrame, cols: Iterable[str]) -> pd.Series:
    """Verilen kolonların skewness'ini döner (sıralı, mutlak değere göre azalan)."""
    skew = df[cols].skew(numeric_only=True)
    return skew.reindex(skew.abs().sort_values(ascending=False).index)


def select_log_columns(
    df: pd.DataFrame,
    cols: Iterable[str],
    skew_threshold: float = 1.0,
    require_nonneg: bool = True,
) -> list[str]:
    """Log dönüşümü adayı kolonları seçer.

    Kriter: |skew| > threshold VE (require_nonneg=True ise) tüm değerler >= 0.
    NDVI gibi negatif değer içeren kolonları otomatik atlamak için
    ``require_nonneg`` default True.
    """
    selected = []
    for c in cols:
        s = float(df[c].skew())
        min_val = float(df[c].min())
        if abs(s) > skew_threshold and (not require_nonneg or min_val >= 0):
            selected.append(c)
    return selected


def apply_standardization(
    df: pd.DataFrame,
    cols: Iterable[str],
    skew_threshold: float = 1.0,
    log_suffix: str = "_log",
    z_suffix: str = "_z",
    inplace: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """İki aşamalı standardizasyon: skewed olanlara log1p, hepsine z-skor.

    Parameters
    ----------
    df : DataFrame
        Veri.
    cols : iterable of str
        Standardize edilecek kolonlar.
    skew_threshold : float
        |skew| > threshold olan kolonlara log1p uygulanır.
    log_suffix, z_suffix : str
        Yeni kolon adlarına eklenecek son ekler.
    inplace : bool
        ``True`` ise ``df``'i değiştirir; ``False`` ise kopya döner.

    Returns
    -------
    DataFrame
        Orijinal kolonlar + (varsa) ``{col}_log`` + ``{col}_z``.
    info : dict
        ``log_cols``, ``zscore_params`` (her kolon için mean/std).
    """
    if not inplace:
        df = df.copy()

    cols = list(cols)
    log_cols = select_log_columns(df, cols, skew_threshold=skew_threshold)

    # 1) Log1p
    for c in log_cols:
        df[f"{c}{log_suffix}"] = np.log1p(df[c].clip(lower=0))

    # 2) Z-skor (log varsa log'lu üzerinden, yoksa orijinal üzerinden)
    zscore_params = {}
    for c in cols:
        src_col = f"{c}{log_suffix}" if c in log_cols else c
        m = float(df[src_col].mean())
        s = float(df[src_col].std())
        df[f"{c}{z_suffix}"] = (df[src_col] - m) / s if s > 0 else 0.0
        zscore_params[c] = {"source": src_col, "mean": m, "std": s}

    return df, {
        "log_cols": log_cols,
        "zscore_params": zscore_params,
        "skew_threshold": skew_threshold,
    }
