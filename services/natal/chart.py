from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field

from services.astro_rules.angles import normalize_angle_deg
from services.astro_rules.aspects import aspect_between
from services.astro_rules.signs import (
    ELEMENT_BY_SIGN,
    MODALITY_BY_SIGN,
    SIGNS,
    placement_for_longitude,
)
from services.ephemeris.provider import DEFAULT_BODIES, EphemerisProvider, PlanetaryPosition
from services.ephemeris.swiss_provider import SwissEphemerisProvider

HOUSE_SYSTEM_CODES = {
    "placidus": b"P",
    "koch": b"K",
    "equal": b"E",
    "whole_sign": b"W",
}

SUPPORTED_ZODIAC_TYPES = frozenset({"tropical"})

NATAL_BODIES = DEFAULT_BODIES


class BirthPlace(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    country: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timezone: str


PLACE_CATALOG: tuple[BirthPlace, ...] = (
    BirthPlace(
        name="Warszawa",
        country="Poland",
        latitude=52.2297,
        longitude=21.0122,
        timezone="Europe/Warsaw",
    ),
    BirthPlace(
        name="Krakow",
        country="Poland",
        latitude=50.0647,
        longitude=19.9450,
        timezone="Europe/Warsaw",
    ),
    BirthPlace(
        name="Gdansk",
        country="Poland",
        latitude=54.3520,
        longitude=18.6466,
        timezone="Europe/Warsaw",
    ),
    BirthPlace(
        name="Bucharest",
        country="Romania",
        latitude=44.4268,
        longitude=26.1025,
        timezone="Europe/Bucharest",
    ),
    BirthPlace(
        name="London",
        country="United Kingdom",
        latitude=51.5072,
        longitude=-0.1276,
        timezone="Europe/London",
    ),
    BirthPlace(
        name="New York",
        country="United States",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
    ),
    BirthPlace(
        name="Los Angeles",
        country="United States",
        latitude=34.0522,
        longitude=-118.2437,
        timezone="America/Los_Angeles",
    ),
    BirthPlace(
        name="Paris",
        country="France",
        latitude=48.8566,
        longitude=2.3522,
        timezone="Europe/Paris",
    ),
    BirthPlace(
        name="Berlin",
        country="Germany",
        latitude=52.5200,
        longitude=13.4050,
        timezone="Europe/Berlin",
    ),
    BirthPlace(
        name="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
    ),
)


class NatalPlanet(BaseModel):
    model_config = ConfigDict(frozen=True)

    body: str
    longitude_deg: float
    wheel_angle_deg: float
    sign: str
    degree_in_sign: float
    element: str
    modality: str
    house: int | None = None
    retrograde: bool


class NatalHouse(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int
    longitude_deg: float
    wheel_angle_deg: float
    sign: str
    degree_in_sign: float


class NatalAxis(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    longitude_deg: float
    wheel_angle_deg: float


class NatalAspect(BaseModel):
    model_config = ConfigDict(frozen=True)

    body_a: str
    body_b: str
    aspect: str
    exact_angle_deg: float
    orb_deg: float
    closeness: float


class NatalSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    elements: dict[str, int]
    modalities: dict[str, int]
    dominant_element: str | None
    dominant_modality: str | None
    dominant_planets: list[str]


class NatalChart(BaseModel):
    model_config = ConfigDict(frozen=True)

    calculation_status: str
    accuracy_note: str
    provider: str
    ephemeris_version: str
    zodiac_type: str
    house_system: str
    birth_datetime_local: str
    birth_datetime_utc: str
    place: BirthPlace
    unknown_time: bool
    planets: list[NatalPlanet]
    houses: list[NatalHouse]
    axes: list[NatalAxis]
    aspects: list[NatalAspect]
    summary: NatalSummary
    warnings: list[str]


@dataclass(frozen=True)
class NatalChartInput:
    birth_date: date
    birth_time: time | None
    place: BirthPlace
    house_system: str = "placidus"
    zodiac_type: str = "tropical"
    unknown_time: bool = False


def search_places(query: str, country: str | None = None, limit: int = 12) -> list[BirthPlace]:
    normalized_query = query.strip().lower()
    normalized_country = (country or "").strip().lower()
    if not normalized_query and not normalized_country:
        return list(PLACE_CATALOG[:limit])
    matches = []
    for place in PLACE_CATALOG:
        haystack = f"{place.name} {place.country}".lower()
        country_ok = not normalized_country or normalized_country in place.country.lower()
        query_ok = not normalized_query or normalized_query in haystack
        if country_ok and query_ok:
            matches.append(place)
    return matches[:limit]


def resolve_place(
    *,
    birthplace: str,
    country: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: str | None = None,
) -> BirthPlace:
    if latitude is not None and longitude is not None and timezone:
        _validate_timezone(timezone)
        return BirthPlace(
            name=birthplace.strip() or "Manual coordinates",
            country=(country or "Manual").strip() or "Manual",
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )

    matches = search_places(birthplace, country=country, limit=1)
    if matches:
        return matches[0]
    msg = (
        "Birthplace is not in the local place catalog. Provide latitude, longitude "
        "and timezone, or add the city to the catalog."
    )
    raise ValueError(msg)


def calculate_natal_chart(
    *,
    chart_input: NatalChartInput,
    provider: EphemerisProvider,
) -> NatalChart:
    house_system_key = chart_input.house_system.strip().lower()
    if house_system_key not in HOUSE_SYSTEM_CODES:
        msg = f"Unsupported house system: {chart_input.house_system}"
        raise ValueError(msg)
    zodiac_type = chart_input.zodiac_type.strip().lower()
    if zodiac_type not in SUPPORTED_ZODIAC_TYPES:
        msg = f"Unsupported zodiac type: {chart_input.zodiac_type}"
        raise ValueError(msg)

    warnings: list[str] = []
    local_time = chart_input.birth_time or time(12, 0)
    if chart_input.unknown_time or chart_input.birth_time is None:
        warnings.append(
            "Birth time is unknown; planets are calculated for local noon, "
            "and houses/ASC/MC are intentionally omitted."
        )
    local_dt = datetime.combine(chart_input.birth_date, local_time).replace(
        tzinfo=ZoneInfo(chart_input.place.timezone)
    )
    utc_dt = local_dt.astimezone(UTC)
    state = provider.compute_state(utc_dt, bodies=NATAL_BODIES)
    houses: list[NatalHouse] = []
    axes: list[NatalAxis] = []
    if not chart_input.unknown_time and chart_input.birth_time is not None:
        houses, axes = _calculate_houses(
            provider=provider,
            julian_day_ut=state.julian_day_ut,
            latitude=chart_input.place.latitude,
            longitude=chart_input.place.longitude,
            house_system_code=HOUSE_SYSTEM_CODES[house_system_key],
        )
    planets = [
        _natal_planet(position, houses=houses)
        for position in state.positions
    ]
    aspects = _natal_aspects(state.positions)
    summary = _natal_summary(planets)
    status = "real_backend"
    note = (
        "Calculated with Swiss Ephemeris backend."
        if isinstance(provider, SwissEphemerisProvider)
        else "Calculated with the configured ephemeris provider."
    )
    return NatalChart(
        calculation_status=status,
        accuracy_note=note,
        provider=state.ephemeris_version,
        ephemeris_version=state.ephemeris_version,
        zodiac_type=zodiac_type,
        house_system=house_system_key,
        birth_datetime_local=local_dt.isoformat(),
        birth_datetime_utc=utc_dt.isoformat(),
        place=chart_input.place,
        unknown_time=chart_input.unknown_time,
        planets=planets,
        houses=houses,
        axes=axes,
        aspects=aspects,
        summary=summary,
        warnings=warnings,
    )


def wheel_angle_for_longitude(longitude_deg: float) -> float:
    """Map zodiac longitude to an SVG wheel angle with Aries at the top."""
    return normalize_angle_deg(longitude_deg - 90.0)


def polar_point(center: float, radius: float, angle_deg: float) -> dict[str, float]:
    angle_rad = math.radians(angle_deg)
    return {
        "x": center + math.cos(angle_rad) * radius,
        "y": center + math.sin(angle_rad) * radius,
    }


def opposite_angle(longitude_deg: float) -> float:
    return normalize_angle_deg(longitude_deg + 180.0)


def _validate_timezone(timezone: str) -> None:
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        msg = f"Unsupported timezone: {timezone}"
        raise ValueError(msg) from exc


def _calculate_houses(
    *,
    provider: EphemerisProvider,
    julian_day_ut: float,
    latitude: float,
    longitude: float,
    house_system_code: bytes,
) -> tuple[list[NatalHouse], list[NatalAxis]]:
    swe = getattr(provider, "_swe", None)
    if swe is None or not hasattr(swe, "houses_ex"):
        msg = "House calculation requires Swiss Ephemeris provider."
        raise ValueError(msg)
    cusps, ascmc = swe.houses_ex(
        julian_day_ut,
        latitude,
        longitude,
        house_system_code,
    )
    houses = [_natal_house(index + 1, longitude_deg) for index, longitude_deg in enumerate(cusps)]
    asc = normalize_angle_deg(float(ascmc[0]))
    mc = normalize_angle_deg(float(ascmc[1]))
    axes = [
        _axis("ASC", asc),
        _axis("DSC", opposite_angle(asc)),
        _axis("MC", mc),
        _axis("IC", opposite_angle(mc)),
    ]
    return houses, axes


def _natal_house(number: int, longitude_deg: float) -> NatalHouse:
    placement = placement_for_longitude(longitude_deg)
    return NatalHouse(
        number=number,
        longitude_deg=normalize_angle_deg(longitude_deg),
        wheel_angle_deg=wheel_angle_for_longitude(longitude_deg),
        sign=placement.sign,
        degree_in_sign=placement.degree_in_sign,
    )


def _axis(name: str, longitude_deg: float) -> NatalAxis:
    return NatalAxis(
        name=name,
        longitude_deg=normalize_angle_deg(longitude_deg),
        wheel_angle_deg=wheel_angle_for_longitude(longitude_deg),
    )


def _natal_planet(position: PlanetaryPosition, houses: list[NatalHouse]) -> NatalPlanet:
    placement = placement_for_longitude(position.longitude_deg)
    return NatalPlanet(
        body=position.body,
        longitude_deg=position.longitude_deg,
        wheel_angle_deg=wheel_angle_for_longitude(position.longitude_deg),
        sign=placement.sign,
        degree_in_sign=placement.degree_in_sign,
        element=placement.element,
        modality=placement.modality,
        house=_house_for_longitude(position.longitude_deg, houses) if houses else None,
        retrograde=position.retrograde,
    )


def _natal_aspects(positions: tuple[PlanetaryPosition, ...]) -> list[NatalAspect]:
    aspects: list[NatalAspect] = []
    for left_index, left in enumerate(positions):
        for right in positions[left_index + 1 :]:
            hit = aspect_between(left, right)
            if hit is None:
                continue
            aspects.append(
                NatalAspect(
                    body_a=hit.body_a,
                    body_b=hit.body_b,
                    aspect=hit.aspect,
                    exact_angle_deg=hit.exact_angle_deg,
                    orb_deg=hit.orb_deg,
                    closeness=hit.closeness,
                )
            )
    return sorted(aspects, key=lambda item: (item.orb_deg, item.body_a, item.body_b))


def _natal_summary(planets: list[NatalPlanet]) -> NatalSummary:
    elements = Counter(planet.element for planet in planets)
    modalities = Counter(planet.modality for planet in planets)
    element_counts = {
        element: elements.get(element, 0)
        for element in ("fire", "earth", "air", "water")
    }
    modality_counts = {
        modality: modalities.get(modality, 0)
        for modality in ("cardinal", "fixed", "mutable")
    }
    return NatalSummary(
        elements=element_counts,
        modalities=modality_counts,
        dominant_element=_dominant_key(element_counts),
        dominant_modality=_dominant_key(modality_counts),
        dominant_planets=[planet.body for planet in planets[:3]],
    )


def _dominant_key(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _house_for_longitude(longitude_deg: float, houses: list[NatalHouse]) -> int | None:
    if len(houses) != 12:
        return None
    longitude = normalize_angle_deg(longitude_deg)
    for index, house in enumerate(houses):
        next_house = houses[(index + 1) % 12]
        if _longitude_in_segment(longitude, house.longitude_deg, next_house.longitude_deg):
            return house.number
    return None


def _longitude_in_segment(value: float, start: float, end: float) -> bool:
    value = normalize_angle_deg(value)
    start = normalize_angle_deg(start)
    end = normalize_angle_deg(end)
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def sign_glyph(sign: str) -> str:
    glyphs = {
        "Aries": "♈",
        "Taurus": "♉",
        "Gemini": "♊",
        "Cancer": "♋",
        "Leo": "♌",
        "Virgo": "♍",
        "Libra": "♎",
        "Scorpio": "♏",
        "Sagittarius": "♐",
        "Capricorn": "♑",
        "Aquarius": "♒",
        "Pisces": "♓",
    }
    return glyphs.get(sign, sign[:2])


def zodiac_segments() -> list[dict[str, str | int | float]]:
    return [
        {
            "sign": sign,
            "glyph": sign_glyph(sign),
            "element": ELEMENT_BY_SIGN[sign],
            "modality": MODALITY_BY_SIGN[sign],
            "start_longitude_deg": index * 30.0,
            "wheel_angle_deg": wheel_angle_for_longitude(index * 30.0 + 15.0),
        }
        for index, sign in enumerate(SIGNS)
    ]
