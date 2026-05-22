from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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

