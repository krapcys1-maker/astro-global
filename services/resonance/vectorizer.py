from __future__ import annotations

import itertools

import numpy as np
from pydantic import BaseModel, ConfigDict

from services.astro_rules.angles import angular_distance_deg, circular_features_deg
from services.astro_rules.aspects import aspect_between
from services.astro_rules.ingress import ingress_proximity
from services.astro_rules.retrograde import is_retrograde, station_proximity
from services.astro_rules.signs import placement_for_longitude
from services.ephemeris.provider import PlanetaryState
from services.resonance.cycles import cycle_contribution_from_aspect

GLOBAL_SLOW_PROFILE_ID = "global_slow_v1"
GLOBAL_SLOW_VECTOR_VERSION = "global_slow_v1.0"
GLOBAL_SLOW_BODIES = ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
ELEMENTS = ("fire", "earth", "air", "water")
MODALITIES = ("cardinal", "fixed", "mutable")


class VectorizationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    profile_id: str
    vector_version: str
    vector: np.ndarray
    feature_groups: dict[str, list[float]]
    feature_debug_json: dict[str, object]
    cycle_strength_debug_json: dict[str, object]


def _normalize_group(values: list[float]) -> list[float]:
    if not values:
        return []
    array = np.asarray(values, dtype=np.float64)
    max_abs = float(np.max(np.abs(array)))
    if max_abs == 0.0:
        return [0.0 for _ in values]
    return (array / max_abs).tolist()


def _flatten_groups(groups: dict[str, list[float]]) -> np.ndarray:
    flattened: list[float] = []
    for key in sorted(groups):
        flattened.extend(groups[key])
    return np.asarray(flattened, dtype=np.float64)


def vectorize_global_slow(state: PlanetaryState) -> VectorizationResult:
    positions = {body: state.position_by_body(body) for body in GLOBAL_SLOW_BODIES}
    outer_phase: list[float] = []
    aspect_channels: list[float] = []
    sign_context: list[float] = []
    ingress_retrograde: list[float] = []
    rare_patterns: list[float] = []
    pair_debug: list[dict[str, object]] = []
    cycle_contributions = []

    for first_body, second_body in itertools.combinations(GLOBAL_SLOW_BODIES, 2):
        first = positions[first_body]
        second = positions[second_body]
        separation = angular_distance_deg(first.longitude_deg, second.longitude_deg)
        outer_phase.extend(circular_features_deg(separation))
        aspect = aspect_between(first, second)
        if aspect is None:
            aspect_channels.extend([0.0, 0.0, 0.0, 0.0, 0.0])
            pair_debug.append(
                {"pair": [first_body, second_body], "separation_deg": separation, "aspect": None}
            )
            continue

        channels = {
            "conjunction": 0.0,
            "sextile": 0.0,
            "square": 0.0,
            "trine": 0.0,
            "opposition": 0.0,
        }
        channels[aspect.aspect] = aspect.closeness
        aspect_channels.extend(channels.values())
        contribution = cycle_contribution_from_aspect(aspect)
        if contribution is not None:
            cycle_contributions.append(contribution)
        pair_debug.append(
            {
                "pair": [first_body, second_body],
                "separation_deg": separation,
                "aspect": aspect.model_dump(),
                "cycle": contribution.model_dump() if contribution else None,
            }
        )

    element_counts = dict.fromkeys(ELEMENTS, 0.0)
    modality_counts = dict.fromkeys(MODALITIES, 0.0)
    sign_indices: list[int] = []
    for body in GLOBAL_SLOW_BODIES:
        position = positions[body]
        placement = placement_for_longitude(position.longitude_deg)
        element_counts[placement.element] += 1.0
        modality_counts[placement.modality] += 1.0
        sign_indices.append(placement.sign_index)
        sign_context.extend(circular_features_deg(placement.sign_index * 30.0))
        ingress_retrograde.append(1.0 if is_retrograde(position.speed_longitude_deg_per_day) else 0.0)
        ingress_retrograde.append(ingress_proximity(position.longitude_deg))
        ingress_retrograde.append(station_proximity(position.speed_longitude_deg_per_day))

    sign_context.extend(element_counts[element] / len(GLOBAL_SLOW_BODIES) for element in ELEMENTS)
    sign_context.extend(modality_counts[modality] / len(GLOBAL_SLOW_BODIES) for modality in MODALITIES)
    rare_patterns.append(1.0 if len(set(sign_indices)) <= 3 else 0.0)
    rare_patterns.append(
        min(1.0, sum(1 for contribution in cycle_contributions if contribution.role == "primary") / 2.0)
    )

    groups = {
        "aspect_channels": _normalize_group(aspect_channels),
        "ingress_retrograde": _normalize_group(ingress_retrograde),
        "outer_phase": _normalize_group(outer_phase),
        "rare_patterns": _normalize_group(rare_patterns),
        "sign_context": _normalize_group(sign_context),
    }
    primary_cycles = [item for item in cycle_contributions if item.role == "primary"]
    supporting_cycles = [item for item in cycle_contributions if item.role != "primary"]
    return VectorizationResult(
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        vector=_flatten_groups(groups),
        feature_groups=groups,
        feature_debug_json={"pairs": pair_debug},
        cycle_strength_debug_json={
            "primary_cycles": [item.model_dump() for item in primary_cycles],
            "supporting_cycles": [item.model_dump() for item in supporting_cycles],
        },
    )

