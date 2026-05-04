"""DMS koordinat parser testleri."""
from __future__ import annotations

import math

import pytest

from src.coord_utils import dms_to_decimal, parse_coord_string


class TestDmsToDecimal:
    def test_north_hemisphere(self) -> None:
        result = dms_to_decimal('36°51\'52.702" N')
        assert math.isclose(result, 36.864639, abs_tol=1e-5)

    def test_east_hemisphere(self) -> None:
        result = dms_to_decimal('30°25\'4.596" E')
        assert math.isclose(result, 30.417943, abs_tol=1e-5)

    def test_south_hemisphere_negative(self) -> None:
        result = dms_to_decimal('33°51\'30.0" S')
        assert result < 0
        assert math.isclose(result, -33.858333, abs_tol=1e-5)

    def test_west_hemisphere_negative(self) -> None:
        result = dms_to_decimal('118°15\'0.0" W')
        assert result < 0

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            dms_to_decimal("not a coordinate")


class TestParseCoordString:
    def test_typical_lat_lon_order(self) -> None:
        result = parse_coord_string('36°51\'52.702" N  30°25\'4.596" E')
        assert result is not None
        lat, lon = result
        assert math.isclose(lat, 36.864639, abs_tol=1e-5)
        assert math.isclose(lon, 30.417943, abs_tol=1e-5)

    def test_reversed_lon_lat_order(self) -> None:
        # E önce, N sonra — fonksiyon swap edip (lat, lon) dönmeli
        result = parse_coord_string('30°25\'4.596" E  36°51\'52.702" N')
        assert result is not None
        lat, lon = result
        assert math.isclose(lat, 36.864639, abs_tol=1e-5)
        assert math.isclose(lon, 30.417943, abs_tol=1e-5)

    def test_none_input(self) -> None:
        assert parse_coord_string(None) is None

    def test_empty_string(self) -> None:
        assert parse_coord_string("") is None
        assert parse_coord_string("   ") is None

    def test_non_string(self) -> None:
        assert parse_coord_string(42) is None
        assert parse_coord_string(float("nan")) is None

    def test_garbage(self) -> None:
        assert parse_coord_string("foo bar baz") is None

    def test_only_one_component(self) -> None:
        # Tek bileşen — iki gerekli
        assert parse_coord_string('36°51\'52.702" N') is None
