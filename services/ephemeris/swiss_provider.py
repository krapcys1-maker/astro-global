from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path
from typing import Any

from services.ephemeris.astro_profile import DEFAULT_ASTRO_PROFILE_ID
from services.ephemeris.provider import (
    DEFAULT_BODIES,
    PlanetaryPosition,
    PlanetaryState,
    normalize_body_name,
)
from services.ephemeris.time_utils import julian_day_from_datetime, require_utc_datetime

BODY_CODES = {
    "Sun": "SUN",
    "Moon": "MOON",
    "Mercury": "MERCURY",
    "Venus": "VENUS",
    "Mars": "MARS",
    "Jupiter": "JUPITER",
    "Saturn": "SATURN",
    "Uranus": "URANUS",
    "Neptune": "NEPTUNE",
    "Pluto": "PLUTO",
}


def load_swiss_module() -> Any:
    try:
        return importlib.import_module("swisseph")
    except ModuleNotFoundError as exc:
        msg = "Swiss Ephemeris support requires 'pip install -e .[astro]'."
        raise RuntimeError(msg) from exc


def normalize_longitude(value: float) -> float:
    normalized = value % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def unpack_calc_result(result: Any) -> tuple[tuple[float, ...] | list[float], int]:
    if not isinstance(result, tuple):
        msg = "Swiss Ephemeris returned an unexpected calc_ut payload."
        raise ValueError(msg)
    if len(result) == 2:
        values, retflag = result
        return values, int(retflag)
    if len(result) == 3:
        values, retflag, _message = result
        return values, int(retflag)
    msg = "Swiss Ephemeris returned an unexpected calc_ut payload."
    raise ValueError(msg)


class SwissEphemerisProvider:
    def __init__(self, ephemeris_path: Path | str | None = None, swe_module: Any | None = None) -> None:
        self._swe = swe_module or load_swiss_module()
        if ephemeris_path is not None:
            self._swe.set_ephe_path(str(ephemeris_path))
        self._flags_value = self._swe.FLG_SWIEPH | self._swe.FLG_SPEED
        self._flags = ("SWIEPH", "SPEED")

    def compute_state(
        self,
        dt_utc: datetime,
        bodies: tuple[str, ...] = DEFAULT_BODIES,
        astro_profile_id: str = DEFAULT_ASTRO_PROFILE_ID,
    ) -> PlanetaryState:
        utc_dt = require_utc_datetime(dt_utc)
        julian_day_ut = julian_day_from_datetime(self._swe, utc_dt)
        positions: list[PlanetaryPosition] = []
        for raw_body in bodies:
            body = normalize_body_name(raw_body)
            body_code = getattr(self._swe, BODY_CODES[body])
            values, _retflag = unpack_calc_result(
                self._swe.calc_ut(julian_day_ut, body_code, self._flags_value)
            )
            positions.append(
                PlanetaryPosition(
                    body=body,
                    longitude_deg=normalize_longitude(float(values[0])),
                    latitude_deg=float(values[1]),
                    distance_au=float(values[2]) if len(values) > 2 else None,
                    speed_longitude_deg_per_day=float(values[3]),
                )
            )

        version = getattr(self._swe, "version", None)
        ephemeris_version = str(version()) if callable(version) else "unknown"
        return PlanetaryState(
            datetime_utc=utc_dt,
            julian_day_ut=julian_day_ut,
            astro_profile_id=astro_profile_id,
            positions=tuple(positions),
            ephemeris_version=ephemeris_version,
            flags=self._flags,
        )

