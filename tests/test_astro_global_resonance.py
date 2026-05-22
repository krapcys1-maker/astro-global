from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pytest

from services.astro_rules.aspects import aspect_between
from services.ephemeris.provider import PlanetaryPosition, PlanetaryState
from services.resonance.cycles import (
    cycle_contribution_from_aspect,
    cycle_for_pair,
    load_cycle_registry,
)
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.scoring import NarrativeConfidenceBreakdown, PlanetaryScoreBreakdown
from services.resonance.vectorizer import GLOBAL_SLOW_BODIES, vectorize_global_slow


def _state(longitudes: dict[str, float]) -> PlanetaryState:
    positions = []
    for body in ("Sun", "Moon", "Mercury", "Venus", "Mars", *GLOBAL_SLOW_BODIES):
        positions.append(
            PlanetaryPosition(
                body=body,
                longitude_deg=longitudes.get(body, 0.0),
                latitude_deg=0.0,
                speed_longitude_deg_per_day=-0.01 if body == "Saturn" else 0.02,
            )
        )
    return PlanetaryState(
        datetime_utc=datetime(2020, 1, 12, tzinfo=UTC),
        julian_day_ut=2_458_861.5,
        positions=tuple(positions),
        ephemeris_version="test",
        flags=("SWIEPH", "SPEED"),
    )


def test_cycle_registry_contains_all_global_slow_pairs() -> None:
    registry = load_cycle_registry()
    for index, first in enumerate(GLOBAL_SLOW_BODIES):
        for second in GLOBAL_SLOW_BODIES[index + 1 :]:
            assert cycle_for_pair(first, second) is not None
            assert tuple(sorted((first, second))) in registry


def test_cycle_power_marks_saturn_pluto_as_primary_driver() -> None:
    aspect = aspect_between(
        PlanetaryPosition(
            body="Saturn",
            longitude_deg=22.0,
            latitude_deg=0.0,
            speed_longitude_deg_per_day=0.0,
        ),
        PlanetaryPosition(
            body="Pluto",
            longitude_deg=22.2,
            latitude_deg=0.0,
            speed_longitude_deg_per_day=0.0,
        ),
    )
    assert aspect is not None

    contribution = cycle_contribution_from_aspect(aspect)

    assert contribution is not None
    assert contribution.tier == "A_structural"
    assert contribution.role == "primary"
    assert contribution.contribution > 0.80


def test_planetary_score_excludes_historical_event_support() -> None:
    planetary = PlanetaryScoreBreakdown(
        structural_similarity=0.7,
        cycle_power_score=0.6,
        rarity_adjusted_percentile=0.5,
    )
    narrative = NarrativeConfidenceBreakdown(
        event_coverage_score=1.0,
        source_quality_score=1.0,
        evidence_confidence=1.0,
    )

    assert planetary.planetary_resonance_score == pytest.approx(0.645)
    assert narrative.narrative_confidence == pytest.approx(1.0)


def test_vectorizer_is_deterministic_and_reports_primary_cycles() -> None:
    state = _state(
        {
            "Jupiter": 10.0,
            "Saturn": 22.0,
            "Uranus": 112.0,
            "Neptune": 250.0,
            "Pluto": 22.2,
        }
    )

    first = vectorize_global_slow(state)
    second = vectorize_global_slow(state)

    np.testing.assert_allclose(first.vector, second.vector)
    assert np.isfinite(first.vector).all()
    assert first.cycle_strength_debug_json["primary_cycles"]


def test_exact_search_self_retrieval() -> None:
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    hits = exact_search(matrix, np.asarray([0.0, 1.0, 0.0]), top_k=2)

    assert hits[0].row_index == 1
    assert hits[0].score == pytest.approx(1.0)


def test_episode_clustering_collapses_neighboring_days() -> None:
    points = [
        CandidatePoint(date=date(2021, 2, 17), score=0.91, row_index=1),
        CandidatePoint(date=date(2021, 2, 24), score=0.88, row_index=2),
        CandidatePoint(date=date(2021, 3, 3), score=0.86, row_index=3),
        CandidatePoint(date=date(2022, 5, 1), score=0.82, row_index=4),
    ]

    episodes = cluster_candidate_points(points)

    assert len(episodes) == 2
    assert episodes[0].best_date == date(2021, 2, 17)
    assert episodes[0].row_indices == (1, 2, 3)
