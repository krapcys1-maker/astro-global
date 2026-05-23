from __future__ import annotations

from datetime import UTC, datetime

import pytest

from services.ephemeris.swiss_provider import (
    SwissEphemerisProvider,
    swiss_module_version,
    unpack_calc_result,
)


class FakeSwissModule:
    FLG_SWIEPH = 2
    FLG_SPEED = 256
    SUN = 0
    MOON = 1
    MERCURY = 2
    VENUS = 3
    MARS = 4
    JUPITER = 5
    SATURN = 6
    URANUS = 7
    NEPTUNE = 8
    PLUTO = 9

    def __init__(self) -> None:
        self.calls: list[tuple[float, int, int]] = []

    def julday(self, year: int, month: int, day: int, hour: float) -> float:
        return 2_400_000.5 + year + month + day + hour

    def calc_ut(self, julian_day: float, body_code: int, flags: int) -> tuple[list[float], int]:
        self.calls.append((julian_day, body_code, flags))
        longitude = (body_code * 37.0 + 361.0) % 360.0
        speed = -0.01 if body_code == self.SATURN else 0.02
        return [longitude, 0.0, 1.0, speed, 0.0, 0.0], flags

    def version(self) -> str:
        return "fake-swe"


def test_swiss_provider_computes_positions_and_speeds() -> None:
    fake = FakeSwissModule()
    provider = SwissEphemerisProvider(swe_module=fake)

    state = provider.compute_state(
        datetime(2026, 5, 22, 12, tzinfo=UTC),
        bodies=("Sun", "Saturn"),
    )

    assert state.ephemeris_version == "fake-swe"
    assert state.flags == ("SWIEPH", "SPEED")
    assert state.position_by_body("Sun").longitude_deg == pytest.approx(1.0)
    assert state.position_by_body("Saturn").retrograde is True
    assert fake.calls[0][2] == fake.FLG_SWIEPH | fake.FLG_SPEED


def test_unpack_calc_result_accepts_realistic_shapes() -> None:
    values, retflag = unpack_calc_result(([1.0, 2.0], 260, "warning"))

    assert values == [1.0, 2.0]
    assert retflag == 260


def test_swiss_module_version_falls_back_to_package_version() -> None:
    class ModuleWithPackageVersion:
        __version__ = "20230604"

    assert swiss_module_version(ModuleWithPackageVersion()) == "20230604"
