from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from services.resonance.scoring import NarrativeConfidenceBreakdown

SOURCE_QUALITY_WEIGHTS = {
    "primary": 1.0,
    "institutional": 0.9,
    "encyclopedic": 0.8,
    "wikidata_seed": 0.65,
    "unknown": 0.0,
}


def source_quality_weight(source_quality: str) -> float:
    return SOURCE_QUALITY_WEIGHTS.get(source_quality, SOURCE_QUALITY_WEIGHTS["unknown"])


def event_coverage_score(
    *, events_found: int, requested_event_limit: int, has_warning: bool
) -> float:
    if events_found <= 0 or requested_event_limit <= 0:
        return 0.0
    score = min(1.0, events_found / requested_event_limit)
    if has_warning:
        score *= 0.65
    return score


def source_quality_score(sources_by_event: Mapping[str, Sequence[Any]]) -> float:
    if not sources_by_event:
        return 0.0
    event_scores: list[float] = []
    for sources in sources_by_event.values():
        if not sources:
            event_scores.append(0.0)
            continue
        event_scores.append(
            max(source_quality_weight(str(source.source_quality)) for source in sources)
        )
    return sum(event_scores) / len(event_scores) if event_scores else 0.0


def evidence_confidence(events: Sequence[Any]) -> float:
    if not events:
        return 0.0
    return sum(float(event.confidence_score) for event in events) / len(events)


def build_narrative_confidence(
    *,
    events: Sequence[Any],
    sources_by_event: Mapping[str, Sequence[Any]],
    coverage_warning: str | None,
    requested_event_limit: int,
) -> NarrativeConfidenceBreakdown:
    return NarrativeConfidenceBreakdown(
        event_coverage_score=event_coverage_score(
            events_found=len(events),
            requested_event_limit=requested_event_limit,
            has_warning=coverage_warning is not None,
        ),
        source_quality_score=source_quality_score(sources_by_event),
        evidence_confidence=evidence_confidence(events),
    )
