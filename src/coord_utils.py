"""DMS (degrees-minutes-seconds) → ondalık derece dönüşümü.

İmar verisindeki ``cografi_koordinat`` kolonu DMS formatındadır:
``"36°51'52.702\\" N  30°25'4.596\\" E"``. Bu modül o stringi (lat, lon)
ondalık derece tuple'ına çevirir.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Tek bir DMS bileşenini yakalayan pattern: 36°51'52.702" N
DMS_PATTERN = re.compile(
    r"(\d+)\s*°\s*(\d+)\s*'\s*([\d.]+)\s*\"?\s*([NSEW])",
    re.IGNORECASE,
)


def dms_to_decimal(dms_str: str) -> float:
    """Tek bir DMS koordinatını ondalık dereceye çevirir.

    Parameters
    ----------
    dms_str : str
        Örn. ``"36°51'52.702\\" N"``.

    Returns
    -------
    float
        Ondalık derece. Güney/Batı için negatif.

    Raises
    ------
    ValueError
        String DMS pattern'iyle eşleşmezse.
    """
    match = DMS_PATTERN.search(dms_str)
    if not match:
        raise ValueError(f"Geçersiz DMS formatı: {dms_str!r}")
    deg, mn, sec, hemi = match.groups()
    decimal = float(deg) + float(mn) / 60 + float(sec) / 3600
    if hemi.upper() in ("S", "W"):
        decimal = -decimal
    return decimal


def parse_coord_string(coord_str: object) -> Optional[Tuple[float, float]]:
    """İki bileşenli DMS stringini (lat, lon) ondalık dereceye çevirir.

    Hem ``"36°51'52\\" N  30°25'4\\" E"`` (lat-lon sırası) hem de
    ``"30°25'4\\" E  36°51'52\\" N"`` (lon-lat sırası) desteklenir;
    sonuç her zaman ``(lat, lon)`` döner.

    Parameters
    ----------
    coord_str : object
        Beklenen tip ``str``. ``None``, NaN veya geçersiz format için
        ``None`` döner — exception fırlatmaz, böylece pandas apply()
        içinde güvenle kullanılabilir.

    Returns
    -------
    tuple of (float, float) or None
        ``(lat, lon)`` veya parse başarısızsa ``None``.
    """
    if not isinstance(coord_str, str) or not coord_str.strip():
        return None

    matches = DMS_PATTERN.findall(coord_str)
    if len(matches) != 2:
        return None

    parsed = []
    hemis = []
    for deg, mn, sec, hemi in matches:
        decimal = float(deg) + float(mn) / 60 + float(sec) / 3600
        hemi_u = hemi.upper()
        if hemi_u in ("S", "W"):
            decimal = -decimal
        parsed.append(decimal)
        hemis.append(hemi_u)

    # Hemisfer sırası: ilk N/S, sonra E/W mi yoksa tersi mi?
    if hemis[0] in ("N", "S") and hemis[1] in ("E", "W"):
        return parsed[0], parsed[1]
    if hemis[0] in ("E", "W") and hemis[1] in ("N", "S"):
        return parsed[1], parsed[0]
    return None
