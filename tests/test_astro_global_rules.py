from __future__ import annotations

import pytest

from services.astro_rules.angles import angular_distance_deg, circular_features_deg
from services.astro_rules.aspects import aspect_between, orb_closeness
from services.astro_rules.ingress import distance_to_sign_boundary_deg
from services.astro_rules.retrograde import is_retrograde
from services.astro_rules.signs import placement_for_longitude
from services.ephemeris.provider import PlanetaryPosition
from services.ephemeris.time_utils import format_historical_year, historical_bce_to_astro_year


def _position(body: str, longitude: float, speed: float = 0.1) -> PlanetaryPosition:
    return PlanetaryPosition(
        body=body,
        longitude_deg=longitude,
        latitude_deg=0.0,
        speed_longitude_deg_per_day=speed,
    )


def test_angular_distance_wraps_across_zero() -> None:
    assert angular_distance_deg(359, 1) == pytest.approx(2)
    assert angular_distance_deg(1, 359) == pytest.approx(2)
    assert angular_distance_deg(10, 190) == pytest.approx(180)
    assert angular_distance_deg(0, 360) == pytest.approx(0)


def test_circular_features_keep_359_and_1_close() -> None:
    first = circular_features_deg(359)
    second = circular_features_deg(1)

    dot = first[0] * second[0] + first[1] * second[1]

    assert dot > 0.99


def test_bce_mapping_never_displays_zero_ce() -> None:
    assert historical_bce_to_astro_year(1) == 0
    assert historical_bce_to_astro_year(500) == -499
    assert format_historical_year(0) == "1 BCE"
    assert format_historical_year(-499) == "500 BCE"
    assert format_historical_year(1) == "1 CE"


def test_sign_boundaries_are_stable() -> None:
    assert placement_for_longitude(0.0).sign == "Aries"
    assert placement_for_longitude(29.999).sign == "Aries"
    assert placement_for_longitude(30.0).sign == "Taurus"
    assert placement_for_longitude(359.999).sign == "Pisces"


def test_retrograde_comes_from_negative_speed() -> None:
    assert is_retrograde(-0.01) is True
    assert is_retrograde(0.0) is False
    assert is_retrograde(0.01) is False


def test_aspect_orb_boundaries() -> None:
    hit = aspect_between(_position("Saturn", 359), _position("Pluto", 1))
    assert hit is not None
    assert hit.aspect == "conjunction"
    assert hit.orb_deg == pytest.approx(2)

    outside = aspect_between(_position("Saturn", 0), _position("Pluto", 7))
    assert outside is None
    assert orb_closeness(0.0, 5.0) == pytest.approx(1.0)
    assert orb_closeness(5.0, 5.0) == pytest.approx(0.0)


def test_ingress_boundary_distance() -> None:
    assert distance_to_sign_boundary_deg(0.25) == pytest.approx(0.25)
    assert distance_to_sign_boundary_deg(29.75) == pytest.approx(0.25)
    assert distance_to_sign_boundary_deg(15.0) == pytest.approx(15.0)

