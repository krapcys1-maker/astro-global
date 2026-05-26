from __future__ import annotations

from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.ephemeris.provider import PlanetaryPosition
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.natal.chart import (
    BirthPlace,
    NatalChartInput,
    _natal_aspects,
    calculate_natal_chart,
    polar_point,
    resolve_place,
    wheel_angle_for_longitude,
)

AUTH_HEADERS = {"x-astro-global-session": "test-token"}


def test_natal_wheel_longitude_maps_aries_to_top() -> None:
    assert wheel_angle_for_longitude(0.0) == pytest.approx(270.0)
    assert wheel_angle_for_longitude(90.0) == pytest.approx(0.0)
    top = polar_point(360, 200, wheel_angle_for_longitude(0.0))
    assert top["x"] == pytest.approx(360.0)
    assert top["y"] == pytest.approx(160.0)


def test_natal_aspects_connect_expected_planets() -> None:
    positions = (
        PlanetaryPosition(
            body="Sun",
            longitude_deg=10.0,
            latitude_deg=0.0,
            speed_longitude_deg_per_day=1.0,
        ),
        PlanetaryPosition(
            body="Moon",
            longitude_deg=190.0,
            latitude_deg=0.0,
            speed_longitude_deg_per_day=1.0,
        ),
        PlanetaryPosition(
            body="Mercury",
            longitude_deg=70.0,
            latitude_deg=0.0,
            speed_longitude_deg_per_day=1.0,
        ),
    )

    aspects = _natal_aspects(positions)

    assert {(aspect.body_a, aspect.body_b, aspect.aspect) for aspect in aspects} >= {
        ("Sun", "Moon", "opposition"),
        ("Sun", "Mercury", "sextile"),
    }


def test_resolve_place_uses_catalog_and_manual_timezone() -> None:
    warsaw = resolve_place(birthplace="Warszawa", country="Poland")
    assert warsaw.timezone == "Europe/Warsaw"

    manual = resolve_place(
        birthplace="Custom",
        country="Test",
        latitude=10.0,
        longitude=20.0,
        timezone="UTC",
    )
    assert manual.latitude == 10.0
    assert manual.longitude == 20.0


def test_calculate_natal_chart_axes_are_opposite_with_swiss() -> None:
    pytest.importorskip("swisseph")
    chart = calculate_natal_chart(
        chart_input=NatalChartInput(
            birth_date=date(2000, 1, 1),
            birth_time=time(12, 0),
            place=BirthPlace(
                name="Warszawa",
                country="Poland",
                latitude=52.2297,
                longitude=21.0122,
                timezone="Europe/Warsaw",
            ),
        ),
        provider=SwissEphemerisProvider(),
    )

    axes = {axis.name: axis.longitude_deg for axis in chart.axes}
    assert len(chart.houses) == 12
    assert [house.number for house in chart.houses] == list(range(1, 13))
    assert (axes["ASC"] - axes["DSC"]) % 360 == pytest.approx(180.0)
    assert (axes["MC"] - axes["IC"]) % 360 == pytest.approx(180.0)
    assert all(0.0 <= planet.wheel_angle_deg < 360.0 for planet in chart.planets)
    label_points = [
        polar_point(360, 253 + (index % 2) * 12, planet.wheel_angle_deg)
        for index, planet in enumerate(chart.planets)
    ]
    for left_index, left in enumerate(label_points):
        for right in label_points[left_index + 1 :]:
            distance = ((left["x"] - right["x"]) ** 2 + (left["y"] - right["y"]) ** 2) ** 0.5
            assert distance > 18


def test_natal_chart_unknown_time_omits_houses() -> None:
    pytest.importorskip("swisseph")
    chart = calculate_natal_chart(
        chart_input=NatalChartInput(
            birth_date=date(1990, 1, 1),
            birth_time=None,
            place=BirthPlace(
                name="London",
                country="United Kingdom",
                latitude=51.5072,
                longitude=-0.1276,
                timezone="Europe/London",
            ),
            unknown_time=True,
        ),
        provider=SwissEphemerisProvider(),
    )

    assert chart.houses == []
    assert chart.axes == []
    assert chart.warnings


def test_natal_chart_api_returns_real_backend_payload() -> None:
    pytest.importorskip("swisseph")
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/natal-chart/calculate",
        headers=AUTH_HEADERS,
        json={
            "birth_date": "1990-01-01",
            "birth_time": "12:00",
            "birthplace": "Warszawa",
            "country": "Poland",
            "house_system": "placidus",
            "zodiac_type": "tropical",
            "provider": "swiss",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["calculation_status"] == "real_backend"
    assert len(payload["planets"]) == 10
    assert len(payload["houses"]) == 12
    assert payload["axes"][0]["name"] == "ASC"


def test_locations_search_endpoint() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/locations/search?q=Warsz", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()[0]["timezone"] == "Europe/Warsaw"
