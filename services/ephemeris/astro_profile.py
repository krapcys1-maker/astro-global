from __future__ import annotations

from pydantic import BaseModel, ConfigDict

DEFAULT_ASTRO_PROFILE_ID = "tropical_geocentric_apparent_v1"


class AstroProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    astro_profile_id: str = DEFAULT_ASTRO_PROFILE_ID
    observer: str = "geocentric"
    time_input: str = "UTC"
    julian_day: str = "UT"
    zodiac: str = "tropical"
    coordinate_system: str = "ecliptic_longitude_latitude"
    position_type: str = "apparent"

