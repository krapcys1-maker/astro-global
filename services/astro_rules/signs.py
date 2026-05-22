from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from services.astro_rules.angles import normalize_angle_deg

SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

ELEMENT_BY_SIGN = {
    "Aries": "fire",
    "Leo": "fire",
    "Sagittarius": "fire",
    "Taurus": "earth",
    "Virgo": "earth",
    "Capricorn": "earth",
    "Gemini": "air",
    "Libra": "air",
    "Aquarius": "air",
    "Cancer": "water",
    "Scorpio": "water",
    "Pisces": "water",
}

MODALITY_BY_SIGN = {
    "Aries": "cardinal",
    "Cancer": "cardinal",
    "Libra": "cardinal",
    "Capricorn": "cardinal",
    "Taurus": "fixed",
    "Leo": "fixed",
    "Scorpio": "fixed",
    "Aquarius": "fixed",
    "Gemini": "mutable",
    "Virgo": "mutable",
    "Sagittarius": "mutable",
    "Pisces": "mutable",
}


class SignPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    sign: str
    sign_index: int
    degree_in_sign: float
    element: str
    modality: str


def sign_index_for_longitude(longitude_deg: float) -> int:
    return int(normalize_angle_deg(longitude_deg) // 30.0)


def placement_for_longitude(longitude_deg: float) -> SignPlacement:
    sign_index = sign_index_for_longitude(longitude_deg)
    sign = SIGNS[sign_index]
    return SignPlacement(
        sign=sign,
        sign_index=sign_index,
        degree_in_sign=normalize_angle_deg(longitude_deg) % 30.0,
        element=ELEMENT_BY_SIGN[sign],
        modality=MODALITY_BY_SIGN[sign],
    )
