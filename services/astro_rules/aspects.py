from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from services.astro_rules.angles import angular_distance_deg
from services.ephemeris.provider import PlanetaryPosition


class AspectDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    angle_deg: float
    default_orb_deg: float
    phase_role: str
    phase_weight: float


MAJOR_ASPECTS = (
    AspectDefinition(
        name="conjunction", angle_deg=0.0, default_orb_deg=5.0, phase_role="hard", phase_weight=1.0
    ),
    AspectDefinition(
        name="sextile",
        angle_deg=60.0,
        default_orb_deg=3.5,
        phase_role="supporting",
        phase_weight=0.40,
    ),
    AspectDefinition(
        name="square", angle_deg=90.0, default_orb_deg=4.5, phase_role="hard", phase_weight=0.88
    ),
    AspectDefinition(
        name="trine",
        angle_deg=120.0,
        default_orb_deg=4.0,
        phase_role="supporting",
        phase_weight=0.55,
    ),
    AspectDefinition(
        name="opposition",
        angle_deg=180.0,
        default_orb_deg=5.0,
        phase_role="hard",
        phase_weight=0.92,
    ),
)


class AspectHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    body_a: str
    body_b: str
    aspect: str
    exact_angle_deg: float
    separation_deg: float
    orb_deg: float
    max_orb_deg: float
    phase_role: str
    phase_weight: float
    closeness: float


def orb_closeness(orb_deg: float, max_orb_deg: float) -> float:
    if orb_deg > max_orb_deg:
        return 0.0
    return 1.0 - (orb_deg / max_orb_deg)


def closest_major_aspect(
    separation_deg: float, max_orb_override: float | None = None
) -> AspectHit | None:
    best: tuple[AspectDefinition, float, float] | None = None
    for definition in MAJOR_ASPECTS:
        orb = abs(separation_deg - definition.angle_deg)
        max_orb = max_orb_override or definition.default_orb_deg
        if orb <= max_orb and (best is None or orb < best[1]):
            best = (definition, orb, max_orb)
    if best is None:
        return None
    definition, orb, max_orb = best
    return AspectHit(
        body_a="",
        body_b="",
        aspect=definition.name,
        exact_angle_deg=definition.angle_deg,
        separation_deg=separation_deg,
        orb_deg=orb,
        max_orb_deg=max_orb,
        phase_role=definition.phase_role,
        phase_weight=definition.phase_weight,
        closeness=orb_closeness(orb, max_orb),
    )


def aspect_between(
    first: PlanetaryPosition,
    second: PlanetaryPosition,
    max_orb_override: float | None = None,
) -> AspectHit | None:
    separation = angular_distance_deg(first.longitude_deg, second.longitude_deg)
    hit = closest_major_aspect(separation, max_orb_override=max_orb_override)
    if hit is None:
        return None
    return hit.model_copy(update={"body_a": first.body, "body_b": second.body})
