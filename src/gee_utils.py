"""Google Earth Engine yardımcıları — Landsat LST + Sentinel-2 NDVI/Albedo + ESA WorldCover.

Auth flow:
    >>> import ee
    >>> ee.Authenticate()                    # bir kez, browser açar
    >>> ee.Initialize(project="ee-...")      # her sessionda

Bu modül ``ee``'yi global import etmez; fonksiyonlar lazy import yapar
ki paket import edenler GEE bağımlılığı zorunda kalmasın.
"""
from __future__ import annotations

from typing import Iterable, Optional


def init_ee(project: Optional[str] = None) -> None:
    """Earth Engine'i initialize eder.

    Parameters
    ----------
    project : str, optional
        Google Cloud project ID (örn. ``"ee-ercangpg"``). ``None`` ise
        ``GEE_PROJECT`` environment variable'ı kullanılır.

    Raises
    ------
    RuntimeError
        Project ID bulunamazsa veya init başarısızsa.
    """
    import ee

    if project is None:
        import os
        project = os.environ.get("GEE_PROJECT")
    if not project:
        raise RuntimeError(
            "GEE project ID gerekli. Argüman geçin veya GEE_PROJECT "
            "env variable set edin (PowerShell'de: "
            "$env:GEE_PROJECT = 'ee-XXX')."
        )
    ee.Initialize(project=project)


def _mask_landsat_clouds(image):
    """QA_PIXEL bit-mask kullanarak bulut/gölge/kar maskeleyen Landsat C2L2 ön-işlemcisi.

    Bit'ler (Landsat C2 L2 QA_PIXEL):
        1 = dilated cloud, 3 = cloud, 4 = cloud shadow, 5 = snow.
    """
    import ee

    qa = image.select("QA_PIXEL")
    cloud_bits = (
        (1 << 1)   # dilated cloud
        | (1 << 3) # cloud
        | (1 << 4) # cloud shadow
        | (1 << 5) # snow
    )
    mask = qa.bitwiseAnd(cloud_bits).eq(0)
    return image.updateMask(mask)


def _add_lst_celsius(image):
    """ST_B10 thermal band'ı Kelvin'e ölçeklendirip Celsius LST kolonuna çevirir.

    Landsat C2 L2 ST_B10 ölçek formülü:
        Kelvin = ST_B10 * 0.00341802 + 149.0
        Celsius = Kelvin - 273.15
    """
    import ee

    lst_k = image.select("ST_B10").multiply(0.00341802).add(149.0)
    lst_c = lst_k.subtract(273.15).rename("LST")
    return image.addBands(lst_c)


def landsat_lst_collection(
    region,
    years: Iterable[int],
    months: Iterable[int],
    cloud_cover_max: float = 10.0,
):
    """Landsat 8 + 9 Collection 2 Level-2'den filtrelenmiş ImageCollection döner.

    Parameters
    ----------
    region : ee.Geometry
        Filtre bölgesi (intersect).
    years : iterable of int
        Yıllar (örn. ``[2020, 2021, 2022, 2023, 2024]``).
    months : iterable of int
        Aylar (örn. ``[6, 7, 8]`` yaz için).
    cloud_cover_max : float
        Sahne-seviyesi bulut yüzdesi tavanı.

    Returns
    -------
    ee.ImageCollection
        ``LST`` bandı eklenmiş, bulut maskesi uygulanmış collection.
    """
    import ee

    years = list(years)
    months = list(months)
    start = f"{min(years)}-01-01"
    end = f"{max(years)}-12-31"

    def _filter_one(coll_id: str):
        return (
            ee.ImageCollection(coll_id)
            .filterBounds(region)
            .filterDate(start, end)
            .filter(ee.Filter.calendarRange(min(months), max(months), "month"))
            .filter(ee.Filter.lt("CLOUD_COVER", cloud_cover_max))
        )

    l8 = _filter_one("LANDSAT/LC08/C02/T1_L2")
    l9 = _filter_one("LANDSAT/LC09/C02/T1_L2")
    merged = l8.merge(l9)

    # Sadece istediğimiz takvim ayları kalmalı
    if list(months) != list(range(min(months), max(months) + 1)):
        merged = merged.filter(ee.Filter.calendarRange(
            min(months), max(months), "month"
        ))

    return (
        merged
        .map(_mask_landsat_clouds)
        .map(_add_lst_celsius)
        .select("LST")
    )


def summer_median_lst(
    region,
    years: Iterable[int],
    months: Iterable[int],
    cloud_cover_max: float = 10.0,
):
    """Yaz medyan LST kompoziti (tek bant, °C).

    Returns
    -------
    ee.Image
        Tek-bantlı (``LST``) median image, region'a clip'lenmiş.
    """
    coll = landsat_lst_collection(region, years, months, cloud_cover_max)
    return coll.median().rename("LST").clip(region)


def boundary_to_ee_geometry(boundary_gdf):
    """GeoDataFrame'i ee.Geometry'e çevirir (4326'ya reproject ederek).

    Parameters
    ----------
    boundary_gdf : GeoDataFrame
        Tek satırlı pilot sınır.

    Returns
    -------
    ee.Geometry
    """
    import ee

    # GEE WGS84 lat/lon bekler
    g4326 = boundary_gdf.to_crs("EPSG:4326")
    geom = g4326.geometry.unary_union
    if geom.geom_type == "MultiPolygon":
        coords = [
            [list(map(list, p.exterior.coords))] for p in geom.geoms
        ]
        return ee.Geometry.MultiPolygon(coords)
    coords = [list(map(list, geom.exterior.coords))]
    return ee.Geometry.Polygon(coords)


# =============================================================================
# Sentinel-2 (NDVI + Albedo)
# =============================================================================

def _mask_s2_clouds(image):
    """Sentinel-2 SCL band ile bulut/gölge maskele.

    SCL sınıfları:
        3 = cloud shadow, 8 = cloud medium, 9 = cloud high, 10 = thin cirrus.
    """
    import ee
    scl = image.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
    )
    return image.updateMask(mask)


def _add_ndvi(image):
    """Sentinel-2 SR'a NDVI bandı ekler. NDVI = (B8 - B4) / (B8 + B4)."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi)


def _add_albedo_liang(image):
    """Liang (2001) short-wave broadband albedo, Sentinel-2 bantlarıyla.

    α = 0.356·B2 + 0.130·B4 + 0.373·B8 + 0.085·B11 + 0.072·B12 - 0.0018

    S2 SR ölçek faktörü: 1/10000 (refleksiyon 0-1 aralığına çekilir).
    Referans: Liang, S. (2001). Narrowband to broadband conversions of
    land surface albedo. Remote Sensing of Environment 76(2): 213-238.
    """
    import ee
    scaled = image.select(["B2", "B4", "B8", "B11", "B12"]).divide(10000)
    albedo = (
        scaled.expression(
            "0.356*B2 + 0.130*B4 + 0.373*B8 + 0.085*B11 + 0.072*B12 - 0.0018",
            {
                "B2": scaled.select("B2"),
                "B4": scaled.select("B4"),
                "B8": scaled.select("B8"),
                "B11": scaled.select("B11"),
                "B12": scaled.select("B12"),
            },
        )
        .rename("ALBEDO")
        .clamp(0, 1)
    )
    return image.addBands(albedo)


def s2_summer_median(
    region,
    years: Iterable[int],
    months: Iterable[int],
    cloud_cover_max: float = 20.0,
    bands: Optional[list[str]] = None,
):
    """Sentinel-2 SR Harmonized'dan yaz medyan kompoziti (NDVI + Albedo).

    Parameters
    ----------
    region : ee.Geometry
    years, months : iterable of int
    cloud_cover_max : float
        ``CLOUDY_PIXEL_PERCENTAGE`` tavanı.
    bands : list of str, optional
        Final image'dan select edilecek bantlar. Default
        ``["NDVI", "ALBEDO"]``.

    Returns
    -------
    ee.Image
        ``NDVI`` ve ``ALBEDO`` bantlı, region'a clip'lenmiş median image.
    """
    import ee

    years = list(years)
    months = list(months)
    start = f"{min(years)}-01-01"
    end = f"{max(years)}-12-31"

    coll = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.calendarRange(min(months), max(months), "month"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
        .map(_mask_s2_clouds)
        .map(_add_ndvi)
        .map(_add_albedo_liang)
    )

    bands = bands or ["NDVI", "ALBEDO"]
    return coll.select(bands).median().clip(region)


# =============================================================================
# ESA WorldCover (Geçirimsiz yüzey oranı)
# =============================================================================

def era5_dominant_wind(
    region,
    years: Iterable[int] = (2020, 2021, 2022, 2023, 2024),
    months: Iterable[int] = (6, 7, 8),
    hours_utc: Iterable[int] = (11, 12, 13, 14),
) -> dict:
    """ERA5 hourly'den hakim yaz öğle rüzgar yönü — aggregate_array yöntemi.

    Her image için region-mean u/v hesaplanıp property olarak set edilir,
    sonra ``aggregate_array`` ile scalar listesi indirilir. Memory-friendly.

    Yön formülü: ``(270 - atan2(v, u) * 180/π) mod 360`` — meteorolojik
    "wind FROM" konvansiyonu.
    """
    import ee
    import math
    import numpy as np

    years = list(years)
    months = list(months)
    hours_utc = list(hours_utc)

    annual = []
    all_u = []
    all_v = []
    for year in years:
        coll_y = (
            ee.ImageCollection("ECMWF/ERA5/HOURLY")
            .filterBounds(region)
            .filter(ee.Filter.calendarRange(year, year, "year"))
            .filter(ee.Filter.calendarRange(min(months), max(months), "month"))
            .filter(ee.Filter.calendarRange(min(hours_utc), max(hours_utc), "hour"))
            .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
        )

        def _add_props(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=27830,            # ERA5 native
                bestEffort=True,
            )
            return img.set({
                "mean_u": stats.get("u_component_of_wind_10m"),
                "mean_v": stats.get("v_component_of_wind_10m"),
            })

        coll_with = coll_y.map(_add_props)
        # Scalar listeleri çek
        us = coll_with.aggregate_array("mean_u").getInfo()
        vs = coll_with.aggregate_array("mean_v").getInfo()
        # None'ları temizle
        pairs = [(u, v) for u, v in zip(us, vs)
                 if u is not None and v is not None]
        if not pairs:
            continue
        us_clean, vs_clean = zip(*pairs)
        u_y = float(np.mean(us_clean))
        v_y = float(np.mean(vs_clean))
        annual.append({"year": year, "u": u_y, "v": v_y, "n": len(pairs)})
        all_u.extend(us_clean)
        all_v.extend(vs_clean)

    # Tüm değerlerden scalar mean
    u_all = float(np.mean(all_u))
    v_all = float(np.mean(all_v))
    speed = math.sqrt(u_all**2 + v_all**2)
    direction_from = (270 - math.degrees(math.atan2(v_all, u_all))) % 360

    return {
        "u": u_all,
        "v": v_all,
        "speed_m_s": speed,
        "direction_from_deg": direction_from,
        "n_images": len(all_u),
        "annual": annual,
        "all_u": all_u,
        "all_v": all_v,
        "years": years,
        "months": months,
        "hours_utc": hours_utc,
    }


def era5_wind_distribution(
    region,
    years: Iterable[int] = (2020, 2021, 2022, 2023, 2024),
    months: Iterable[int] = (6, 7, 8),
    hours_utc: Iterable[int] = (11, 12, 13, 14),
) -> "pd.DataFrame":
    """Her saat için u/v — yıl-by-yıl chunked.

    Konyaaltı gibi tek-pikselli bbox için yılda ~360 saat → 5 yıl × 360.
    Yıl bazlı .toList() ile memory limit aşılmaz.
    """
    import ee
    import pandas as pd
    import math

    years = list(years)
    months = list(months)
    hours_utc = list(hours_utc)

    all_records = []
    for year in years:
        coll_y = (
            ee.ImageCollection("ECMWF/ERA5/HOURLY")
            .filterBounds(region)
            .filter(ee.Filter.calendarRange(year, year, "year"))
            .filter(ee.Filter.calendarRange(min(months), max(months), "month"))
            .filter(ee.Filter.calendarRange(min(hours_utc), max(hours_utc), "hour"))
            .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
        )

        def _img_to_feat(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=20000,
                bestEffort=True,
            )
            return ee.Feature(None, {
                "u": stats.get("u_component_of_wind_10m"),
                "v": stats.get("v_component_of_wind_10m"),
                "ts": img.get("system:time_start"),
            })

        fc = ee.FeatureCollection(coll_y.map(_img_to_feat))
        try:
            rows = fc.toList(fc.size()).getInfo()
        except Exception as e:
            print(f"  [warn] {year} skipped: {type(e).__name__}: {e}")
            continue

        for r in rows:
            p = r["properties"]
            if p.get("u") is None or p.get("v") is None:
                continue
            u = float(p["u"])
            v = float(p["v"])
            all_records.append({
                "year": year,
                "ts_ms": int(p["ts"]) if p.get("ts") else None,
                "u": u,
                "v": v,
                "speed": math.sqrt(u**2 + v**2),
                "dir_from": (270 - math.degrees(math.atan2(v, u))) % 360,
            })
    return pd.DataFrame(all_records)


def ghsl_built_height(region, year: int = 2018):
    """GHSL JRC global built-up height image (100 m).

    Parameters
    ----------
    region : ee.Geometry
    year : int
        Default 2018 (P2023A release; tek yıl mevcut).

    Returns
    -------
    ee.Image
        Tek-bant ``BUILT_H`` (metre cinsinden bina yüksekliği). 0 = bina yok.
        Native 100 m. Zonal mean alınınca hücre içi ortalama yükseklik verir.
    """
    import ee
    img = ee.Image(f"JRC/GHSL/P2023A/GHS_BUILT_H/{year}").rename("BUILT_H")
    return img.clip(region)


def esa_worldcover_impervious(region, version: str = "v200"):
    """ESA WorldCover'dan geçirimsiz yüzey (built-up = sınıf 50) binary maskesi.

    Parameters
    ----------
    region : ee.Geometry
    version : str
        ``"v200"`` (2021) veya ``"v100"`` (2020). Default v200.

    Returns
    -------
    ee.Image
        Tek-bant ``IMPERVIOUS`` (uint8: 1 = built-up, 0 = diğer).
        Native çözünürlük 10 m. Zonal mean alınınca hücre içi
        geçirimsiz oranı (%) verir.
    """
    import ee
    wc = ee.ImageCollection(f"ESA/WorldCover/{version}").first()
    impervious = wc.eq(50).rename("IMPERVIOUS").toUint8()
    return impervious.clip(region)
