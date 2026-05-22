from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from services.resonance.scoring import NarrativeConfidenceBreakdown

DEFAULT_SOURCE_QUALITY_CONFIG_PATH = Path(__file__).with_name("source_quality.yaml")
SOURCE_PRECISION_WEIGHTS = {
    "direct": 1.0,
    "contextual": 0.85,
    "broad_context": 0.65,
    "structured_reference": 0.75,
    "unknown": 0.0,
}


def load_source_quality_weights(
    path: Path | str = DEFAULT_SOURCE_QUALITY_CONFIG_PATH,
) -> dict[str, float]:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        msg = "source quality config must be a mapping"
        raise ValueError(msg)
    weights_raw = raw.get("source_quality_weights")
    if not isinstance(weights_raw, Mapping):
        msg = "source quality config must contain source_quality_weights"
        raise ValueError(msg)

    weights: dict[str, float] = {}
    for key, value in weights_raw.items():
        normalized_key = str(key).strip()
        numeric_value = float(value)
        if not normalized_key:
            msg = "source quality keys must be non-empty"
            raise ValueError(msg)
        if not 0.0 <= numeric_value <= 1.0:
            msg = f"source quality weight must be within 0..1: {normalized_key}"
            raise ValueError(msg)
        weights[normalized_key] = numeric_value

    if "unknown" not in weights:
        msg = "source quality config must define unknown"
        raise ValueError(msg)
    return weights


@lru_cache(maxsize=1)
def default_source_quality_weights() -> dict[str, float]:
    return load_source_quality_weights()


def source_quality_weight(
    source_quality: str,
    weights: Mapping[str, float] | None = None,
) -> float:
    active_weights = weights or default_source_quality_weights()
    return active_weights.get(source_quality, active_weights["unknown"])


def source_precision_weight(source_precision: str) -> float:
    return SOURCE_PRECISION_WEIGHTS.get(source_precision, SOURCE_PRECISION_WEIGHTS["unknown"])


def event_coverage_score(
    *, events_found: int, requested_event_limit: int, has_warning: bool
) -> float:
    if events_found <= 0 or requested_event_limit <= 0:
        return 0.0
    score = min(1.0, events_found / requested_event_limit)
    if has_warning:
        score *= 0.65
    return score


def source_quality_score(
    sources_by_event: Mapping[str, Sequence[Any]],
    weights: Mapping[str, float] | None = None,
) -> float:
    if not sources_by_event:
        return 0.0
    active_weights = weights or default_source_quality_weights()
    event_scores: list[float] = []
    for sources in sources_by_event.values():
        if not sources:
            event_scores.append(0.0)
            continue
        event_scores.append(
            max(
                source_quality_weight(str(source.source_quality), active_weights)
                * source_precision_weight(str(getattr(source, "source_precision", "direct")))
                for source in sources
            )
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
