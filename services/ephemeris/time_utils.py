from __future__ import annotations

from datetime import UTC, datetime


def require_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        msg = "datetime must be timezone-aware"
        raise ValueError(msg)
    return dt.astimezone(UTC)


def historical_bce_to_astro_year(bce: int) -> int:
    if bce < 1:
        msg = "BCE year must be >= 1"
        raise ValueError(msg)
    return 1 - bce


def format_historical_year(astro_year: int) -> str:
    if astro_year > 0:
        return f"{astro_year} CE"
    return f"{1 - astro_year} BCE"


def julian_day_from_datetime(swe_module: object, dt_utc: datetime) -> float:
    utc_dt = require_utc_datetime(dt_utc)
    hour = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)
    hour += utc_dt.microsecond / 3_600_000_000.0
    return float(swe_module.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour))

