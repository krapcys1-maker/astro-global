from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from services.resonance.vectorizer import GLOBAL_SLOW_BODIES

MIN_COMPARABLE_INDEX_ROWS = 30
ASPECT_NAMES = ("conjunction", "sextile", "square", "trine", "opposition")
OUTER_SIGN_BODIES = ("Uranus", "Neptune", "Pluto")
OUTER_ASPECT_PAIRS = (
    ("Uranus", "Neptune"),
    ("Uranus", "Pluto"),
    ("Neptune", "Pluto"),
)
SIGN_ELEMENTS = (
    "fire",
    "earth",
    "air",
    "water",
    "fire",
    "earth",
    "air",
    "water",
    "fire",
    "earth",
    "air",
    "water",
)
SIGN_MODALITIES = (
    "cardinal",
    "fixed",
    "mutable",
    "cardinal",
    "fixed",
    "mutable",
    "cardinal",
    "fixed",
    "mutable",
    "cardinal",
    "fixed",
    "mutable",
)

_PAIR_ORDER = [
    (first, second)
    for index, first in enumerate(GLOBAL_SLOW_BODIES)
    for second in GLOBAL_SLOW_BODIES[index + 1 :]
]
_ASPECT_OFFSET = 0
_ASPECT_GROUP_LENGTH = len(_PAIR_ORDER) * len(ASPECT_NAMES)
_INGRESS_GROUP_LENGTH = len(GLOBAL_SLOW_BODIES) * 3
_OUTER_PHASE_GROUP_LENGTH = len(_PAIR_ORDER) * 2
_RARE_PATTERN_GROUP_LENGTH = 2
_SIGN_CONTEXT_OFFSET = (
    _ASPECT_GROUP_LENGTH
    + _INGRESS_GROUP_LENGTH
    + _OUTER_PHASE_GROUP_LENGTH
    + _RARE_PATTERN_GROUP_LENGTH
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _body_index(body: str) -> int:
    return GLOBAL_SLOW_BODIES.index(body)


def _pair_index(first: str, second: str) -> int:
    pair = tuple(sorted((first, second), key=GLOBAL_SLOW_BODIES.index))
    return _PAIR_ORDER.index(pair)


def _sign_index_from_vector(vector: np.ndarray, body: str) -> int:
    body_offset = _SIGN_CONTEXT_OFFSET + _body_index(body) * 2
    x = float(vector[body_offset])
    y = float(vector[body_offset + 1])
    angle = math.degrees(math.atan2(y, x))
    if angle < 0.0:
        angle += 360.0
    return int(round(angle / 30.0)) % 12


def _sign_similarity(left_sign: int, right_sign: int) -> float:
    if left_sign == right_sign:
        return 1.0
    if SIGN_ELEMENTS[left_sign] == SIGN_ELEMENTS[right_sign]:
        return 0.55
    if SIGN_MODALITIES[left_sign] == SIGN_MODALITIES[right_sign]:
        return 0.35
    return 0.15


def outer_sign_environment_similarity(
    query_vector: np.ndarray,
    candidate_vector: np.ndarray,
) -> float:
    similarities = [
        _sign_similarity(
            _sign_index_from_vector(query_vector, body),
            _sign_index_from_vector(candidate_vector, body),
        )
        for body in OUTER_SIGN_BODIES
    ]
    return float(sum(similarities) / len(similarities))


def shared_outer_aspect_similarity(
    query_vector: np.ndarray,
    candidate_vector: np.ndarray,
) -> float:
    strongest = 0.0
    for first, second in OUTER_ASPECT_PAIRS:
        offset = _ASPECT_OFFSET + _pair_index(first, second) * len(ASPECT_NAMES)
        query_channels = query_vector[offset : offset + len(ASPECT_NAMES)]
        candidate_channels = candidate_vector[offset : offset + len(ASPECT_NAMES)]
        strongest = max(strongest, float(np.dot(query_channels, candidate_channels)))
    return _clamp01(strongest)


def calibrate_structural_similarity(
    *,
    raw_score: float,
    query_vector: np.ndarray,
    candidate_vector: np.ndarray,
) -> float:
    """Prevent high match labels without outer-planet epoch support.

    The global_slow_v1 vector is intentionally continuous, so adjacent sign
    placements and broad phase geometry can produce high cosine scores. For
    user-facing resonance confidence, an 80-90% match needs either a compatible
    Uranus/Neptune/Pluto sign environment or a shared outer-planet aspect.
    """

    score = _clamp01(raw_score)
    if score < 0.80:
        return score

    sign_support = outer_sign_environment_similarity(query_vector, candidate_vector)
    outer_aspect_support = shared_outer_aspect_similarity(query_vector, candidate_vector)
    if sign_support >= 0.72 or outer_aspect_support >= 0.45:
        return score

    support = max(sign_support, outer_aspect_support)
    confidence_cap = 0.78 + 0.04 * support
    return min(score, confidence_cap)


class PlanetaryScoreBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    structural_similarity: float = Field(ge=0.0, le=1.0)
    cycle_power_score: float = Field(ge=0.0, le=1.0)
    rarity_adjusted_percentile: float = Field(ge=0.0, le=1.0)

    @property
    def planetary_resonance_score(self) -> float:
        return (
            0.60 * self.structural_similarity
            + 0.25 * self.cycle_power_score
            + 0.15 * self.rarity_adjusted_percentile
        )


class ResonanceStrengthBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    structural_similarity: float = Field(ge=0.0, le=1.0)
    cycle_power_score: float = Field(ge=0.0, le=1.0)
    rarity_adjusted_percentile: float = Field(ge=0.0, le=1.0)
    planetary_resonance_score: float = Field(ge=0.0, le=1.0)
    label: str
    primary_cycle_count: int = Field(ge=0)
    strongest_primary_contribution: float = Field(ge=0.0, le=1.0)
    rare_configuration: bool
    insufficient_comparable_history: bool


class NarrativeConfidenceBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_coverage_score: float = Field(ge=0.0, le=1.0)
    source_quality_score: float = Field(ge=0.0, le=1.0)
    evidence_confidence: float = Field(ge=0.0, le=1.0)

    @property
    def narrative_confidence(self) -> float:
        return (
            0.45 * self.event_coverage_score
            + 0.30 * self.source_quality_score
            + 0.25 * self.evidence_confidence
        )


def cycle_power_score(primary_cycles: Sequence[Mapping[str, Any]]) -> float:
    contributions = sorted(
        (
            _clamp01(float(cycle.get("contribution", 0.0)))
            for cycle in primary_cycles
        ),
        reverse=True,
    )
    if not contributions:
        return 0.0
    # Two strong hard-phase outer cycles are enough to saturate the proof score.
    return _clamp01(sum(contributions[:2]) / 1.2)


def build_resonance_strength_breakdown(
    *,
    structural_similarity: float,
    rarity_adjusted_percentile: float,
    primary_cycles: Sequence[Mapping[str, Any]],
    index_rows: int,
) -> ResonanceStrengthBreakdown:
    primary_cycle_count = len(primary_cycles)
    strongest_primary_contribution = max(
        (_clamp01(float(cycle.get("contribution", 0.0))) for cycle in primary_cycles),
        default=0.0,
    )
    cycle_power = cycle_power_score(primary_cycles)
    planetary = PlanetaryScoreBreakdown(
        structural_similarity=_clamp01(structural_similarity),
        cycle_power_score=cycle_power,
        rarity_adjusted_percentile=_clamp01(rarity_adjusted_percentile),
    )
    score = planetary.planetary_resonance_score
    insufficient = index_rows < MIN_COMPARABLE_INDEX_ROWS
    rare = (
        planetary.rarity_adjusted_percentile >= 0.98
        and cycle_power >= 0.35
        and primary_cycle_count > 0
    )
    if insufficient:
        label = "insufficient_comparable_history"
    elif (
        score >= 0.82
        and cycle_power >= 0.55
        and strongest_primary_contribution >= 0.45
        and primary_cycle_count > 0
    ):
        label = "strong"
    elif rare and score < 0.82:
        label = "rare_configuration"
    elif score >= 0.55:
        label = "moderate"
    else:
        label = "weak"
    return ResonanceStrengthBreakdown(
        structural_similarity=planetary.structural_similarity,
        cycle_power_score=planetary.cycle_power_score,
        rarity_adjusted_percentile=planetary.rarity_adjusted_percentile,
        planetary_resonance_score=score,
        label=label,
        primary_cycle_count=primary_cycle_count,
        strongest_primary_contribution=strongest_primary_contribution,
        rare_configuration=rare,
        insufficient_comparable_history=insufficient,
    )
