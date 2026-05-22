from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest

from scripts import build_planetary_index as index_script
from scripts.benchmark_planetary_index import benchmark_index
from scripts.build_planetary_index import parse_utc
from services.astro_rules.aspects import aspect_between
from services.ephemeris.provider import PlanetaryPosition, PlanetaryState
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.resonance.cycles import (
    cycle_contribution_from_aspect,
    cycle_for_pair,
    load_cycle_registry,
)
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import build_weekly_index
from services.resonance.index_store import INDEX_STORE_VERSION, load_built_index, save_built_index
from services.resonance.scoring import (
    NarrativeConfidenceBreakdown,
    PlanetaryScoreBreakdown,
    build_resonance_strength_breakdown,
    cycle_power_score,
)
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


def test_resonance_strength_requires_primary_outer_cycle_for_strong_label() -> None:
    strength = build_resonance_strength_breakdown(
        structural_similarity=1.0,
        rarity_adjusted_percentile=1.0,
        primary_cycles=[],
        index_rows=100,
    )

    assert strength.label != "strong"
    assert strength.cycle_power_score == 0.0
    assert strength.rare_configuration is False


def test_resonance_strength_labels_strong_primary_hard_cycle() -> None:
    strength = build_resonance_strength_breakdown(
        structural_similarity=0.99,
        rarity_adjusted_percentile=1.0,
        primary_cycles=[
            {"pair": ["Pluto", "Uranus"], "contribution": 0.62},
            {"pair": ["Neptune", "Pluto"], "contribution": 0.38},
        ],
        index_rows=100,
    )

    assert strength.label == "strong"
    assert strength.cycle_power_score == pytest.approx(cycle_power_score([
        {"contribution": 0.62},
        {"contribution": 0.38},
    ]))
    assert strength.planetary_resonance_score > 0.8
    assert strength.rare_configuration is True


def test_resonance_strength_reports_insufficient_history_first() -> None:
    strength = build_resonance_strength_breakdown(
        structural_similarity=1.0,
        rarity_adjusted_percentile=1.0,
        primary_cycles=[{"pair": ["Pluto", "Uranus"], "contribution": 1.0}],
        index_rows=10,
    )

    assert strength.label == "insufficient_comparable_history"
    assert strength.insufficient_comparable_history is True


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


def test_persistent_index_roundtrip(tmp_path: Path) -> None:
    provider = SyntheticEphemerisProvider()
    built = build_weekly_index(
        provider,
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 22, tzinfo=UTC),
        step_days=7,
    )
    output = tmp_path / "proof_index.npz"

    save_built_index(
        built,
        output,
        profile_id="global_slow_v1",
        vector_version="global_slow_v1.0",
        provider="synthetic-dev",
        step_days=7,
    )
    loaded, metadata = load_built_index(output)

    assert metadata["store_version"] == INDEX_STORE_VERSION
    assert metadata["provider"] == "synthetic-dev"
    assert metadata["step_days"] == 7
    assert len(loaded.rows) == len(built.rows)
    assert loaded.rows[0] == built.rows[0]
    np.testing.assert_allclose(loaded.matrix, built.matrix)


def test_build_planetary_index_parse_utc_normalizes_naive_and_z_dates() -> None:
    assert parse_utc("2026-05-22").tzinfo == UTC
    assert parse_utc("2026-05-22T12:00:00Z").isoformat() == "2026-05-22T12:00:00+00:00"


def test_build_planetary_index_supports_synthetic_provider() -> None:
    provider = index_script.build_provider("synthetic")

    state = provider.compute_state(datetime(2026, 5, 22, tzinfo=UTC))

    assert state.ephemeris_version == "synthetic-dev"
    assert index_script.PROVIDER_LABELS["synthetic"] == "synthetic-dev"
    assert index_script.PROVIDER_LABELS["swiss"] == "swiss-ephemeris"


def test_build_planetary_index_reports_missing_swiss_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingSwissProvider:
        def __init__(self, ephemeris_path: Path | None = None) -> None:
            raise RuntimeError("Swiss Ephemeris support requires 'pip install -e .[astro]'.")

    monkeypatch.setattr(index_script, "SwissEphemerisProvider", MissingSwissProvider)

    with pytest.raises(SystemExit, match="Swiss Ephemeris support requires"):
        index_script.build_provider("swiss")


def test_benchmark_planetary_index_reports_build_and_search_metrics() -> None:
    report = benchmark_index(
        provider_name="synthetic",
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_utc=datetime(2026, 1, 22, tzinfo=UTC),
        query_utc=datetime(2026, 1, 8, tzinfo=UTC),
        step_days=7,
        top_k=3,
    )

    assert report.provider == "synthetic-dev"
    assert report.rows == 4
    assert report.dimensions == 104
    assert report.matrix_mb > 0
    assert report.build_seconds >= 0
    assert report.search_seconds >= 0
    assert report.top_score is not None
    assert report.top_datetime_utc is not None
