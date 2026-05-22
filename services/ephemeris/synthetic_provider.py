from __future__ import annotations

from datetime import UTC, datetime

from services.ephemeris.provider import DEFAULT_BODIES, PlanetaryPosition, PlanetaryState


class SyntheticEphemerisProvider:
    """Deterministic development provider used until local Swiss Ephemeris is available."""

    def compute_state(
        self,
        dt_utc: datetime,
        bodies: tuple[str, ...] = DEFAULT_BODIES,
        astro_profile_id: str = "tropical_geocentric_apparent_v1",
    ) -> PlanetaryState:
        query_dt = dt_utc.astimezone(UTC)
        days = (query_dt - datetime(1900, 1, 1, tzinfo=UTC)).days
        periods = {
            "Sun": 365.25,
            "Moon": 27.3,
            "Mercury": 88.0,
            "Venus": 224.7,
            "Mars": 687.0,
            "Jupiter": 4332.6,
            "Saturn": 10759.0,
            "Uranus": 30687.0,
            "Neptune": 60190.0,
            "Pluto": 90560.0,
        }
        positions = []
        for body in bodies:
            period = periods[body]
            longitude = ((days / period) * 360.0) % 360.0
            speed = 360.0 / period
            positions.append(
                PlanetaryPosition(
                    body=body,
                    longitude_deg=longitude,
                    latitude_deg=0.0,
                    speed_longitude_deg_per_day=speed,
                )
            )
        return PlanetaryState(
            datetime_utc=query_dt,
            julian_day_ut=2_415_020.5 + days,
            astro_profile_id=astro_profile_id,
            positions=tuple(positions),
            ephemeris_version="synthetic-dev",
            flags=("SYNTHETIC",),
        )
