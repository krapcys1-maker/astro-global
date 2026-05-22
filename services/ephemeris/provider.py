from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ephemeris.astro_profile import DEFAULT_ASTRO_PROFILE_ID

DEFAULT_BODIES = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)


def normalize_body_name(body: str) -> str:
    normalized = body.strip().lower()
    for candidate in DEFAULT_BODIES:
        if candidate.lower() == normalized:
            return candidate
    msg = f"Unsupported body: {body}"
    raise ValueError(msg)


class PlanetaryPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    body: str
    longitude_deg: float = Field(ge=0.0, lt=360.0)
    latitude_deg: float
    distance_au: float | None = None
    speed_longitude_deg_per_day: float

    @field_validator("body")
    @classmethod
    def _normalize_body(cls, value: str) -> str:
        return normalize_body_name(value)

    @property
    def retrograde(self) -> bool:
        return self.speed_longitude_deg_per_day < 0.0


class PlanetaryState(BaseModel):
    model_config = ConfigDict(frozen=True)

    datetime_utc: datetime
    julian_day_ut: float
    astro_profile_id: str = DEFAULT_ASTRO_PROFILE_ID
    positions: tuple[PlanetaryPosition, ...]
    ephemeris_version: str
    flags: tuple[str, ...]

    def position_by_body(self, body: str) -> PlanetaryPosition:
        normalized = normalize_body_name(body)
        for position in self.positions:
            if position.body == normalized:
                return position
        msg = f"PlanetaryState does not include body: {normalized}"
        raise KeyError(msg)


class EphemerisProvider(Protocol):
    def compute_state(
        self,
        dt_utc: datetime,
        bodies: tuple[str, ...] = DEFAULT_BODIES,
        astro_profile_id: str = DEFAULT_ASTRO_PROFILE_ID,
    ) -> PlanetaryState: ...
