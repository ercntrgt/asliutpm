"""Feature seçimi: VIF analizi + iteratif eleme.

VIF (Variance Inflation Factor): bir özelliğin diğer özelliklerle olan
çoklu doğrusal regresyonundan üretilir. VIF=1 → bağımsız;
VIF>5 → dikkat; VIF>10 → ciddi multicollinearity.

Iteratif yaklaşım: en yüksek VIF'li özelliği at, kalan setle yeniden hesapla,
hepsi eşik altına düşene kadar tekrarla.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd


def compute_vif(
    df: pd.DataFrame,
    cols: Iterable[str],
    fillna_with: float = 0.0,
) -> pd.Series:
    """Verilen kolonlar için VIF hesaplar.

    Parameters
    ----------
    df : DataFrame
    cols : iterable of str
    fillna_with : float
        NaN değerleri (örn. building_height_mean bina olmayan hücreler)
        bu değerle doldurulur. Default 0 (z-skor space'inde mean).

    Returns
    -------
    pd.Series
        Index: kolon adı, value: VIF.
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    cols = list(cols)
    X = df[cols].copy().astype(float)
    X = X.fillna(fillna_with)
    # statsmodels constant ekleme önerir ama VIF için gerekli değil — pure feature matrix
    vif = pd.Series(
        [variance_inflation_factor(X.values, i) for i in range(X.shape[1])],
        index=cols,
        name="VIF",
    )
    return vif.sort_values(ascending=False)


def iterative_vif_drop(
    df: pd.DataFrame,
    cols: Iterable[str],
    threshold: float = 10.0,
    fillna_with: float = 0.0,
    protect: Optional[Iterable[str]] = None,
) -> tuple[list[str], pd.DataFrame]:
    """En yüksek VIF'li olanı atarak hepsi eşik altına düşene kadar iteratif eleme.

    Parameters
    ----------
    df : DataFrame
    cols : iterable of str
        Aday kolonlar.
    threshold : float
        VIF eşiği (default 10).
    fillna_with : float
        NaN doldurma.
    protect : iterable of str, optional
        Bu kolonlar yüksek VIF olsa bile elenmez (örn. domain-critical).

    Returns
    -------
    final_cols : list of str
        Kalan kolonlar.
    history : DataFrame
        Her iterasyonun VIF tablosu (kolon: iter_0, iter_1, ...).
    """
    cols = list(cols)
    protect = set(protect or [])
    remaining = list(cols)
    history = {}
    iter_idx = 0

    while True:
        vif = compute_vif(df, remaining, fillna_with=fillna_with)
        history[f"iter_{iter_idx}"] = vif

        # eşik üstü olanlardan, korunmayanları topla
        candidates = vif[(vif > threshold) & (~vif.index.isin(protect))]
        if candidates.empty:
            break

        # en yüksek VIF'liyi at
        drop_col = candidates.idxmax()
        remaining.remove(drop_col)
        iter_idx += 1

        if len(remaining) <= 1:
            break

    history_df = pd.DataFrame(history)
    return remaining, history_df


def correlation_redundancy(
    df: pd.DataFrame,
    cols: Iterable[str],
    threshold: float = 0.7,
) -> pd.DataFrame:
    """Yüksek pairwise korelasyon olan çiftleri listeler.

    Returns
    -------
    DataFrame
        Kolonlar: ``var_a``, ``var_b``, ``r``. |r| > threshold olanlar.
    """
    cols = list(cols)
    corr = df[cols].corr()
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            if abs(r) > threshold:
                pairs.append({"var_a": a, "var_b": b, "r": round(float(r), 3)})

    if not pairs:
        return pd.DataFrame(columns=["var_a", "var_b", "r"])

    out = pd.DataFrame(pairs)
    out = out.sort_values("r", key=lambda s: s.abs(), ascending=False)
    return out.reset_index(drop=True)
