from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from services.astro_rules.angles import angular_distance_deg
from services.ephemeris.provider import DEFAULT_BODIES
from services.ephemeris.swiss_provider import SwissEphemerisProvider, load_swiss_module

FIXTURE_PATH = (
    Path(__file__).parent / "golden" / "planetary_states" / "jpl_horizons_2026-05-22T12Z.json"
)


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_jpl_horizons_fixture_covers_core_bodies() -> None:
    fixture = load_fixture()
    positions = fixture["positions"]

    assert fixture["source"] == "NASA/JPL Horizons API"
    assert fixture["center"] == "500@399"
    assert fixture["quantities"] == "31"
    assert {position["body"] for position in positions} == set(DEFAULT_BODIES)


@pytest.mark.integration
def test_swiss_ephemeris_matches_jpl_horizons_golden() -> None:
    try:
        load_swiss_module()
    except RuntimeError as exc:
        pytest.skip(str(exc))

    fixture = load_fixture()
    dt_utc = datetime.fromisoformat(str(fixture["datetime_utc"]).replace("Z", "+00:00")).astimezone(
        UTC
    )
    tolerances = fixture["tolerances"]
    expected_by_body = {str(position["body"]): position for position in fixture["positions"]}

    state = SwissEphemerisProvider().compute_state(dt_utc, bodies=DEFAULT_BODIES)

    for body in DEFAULT_BODIES:
        actual = state.position_by_body(body)
        expected = expected_by_body[body]

        assert angular_distance_deg(
            actual.longitude_deg,
            float(expected["longitude_deg"]),
        ) <= float(tolerances["longitude_deg"])
        assert actual.latitude_deg == pytest.approx(
            float(expected["latitude_deg"]),
            abs=float(tolerances["latitude_deg"]),
        )
        assert actual.speed_longitude_deg_per_day == pytest.approx(
            float(expected["speed_longitude_deg_per_day"]),
            abs=float(tolerances["speed_longitude_deg_per_day"]),
        )
