from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MIN_COMPARABLE_INDEX_ROWS = 30


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


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
