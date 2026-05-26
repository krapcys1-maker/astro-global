from __future__ import annotations

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest

from scripts import build_planetary_index as index_script
from scripts.benchmark_planetary_index import benchmark_index
from scripts.build_planetary_index import parse_utc
from services.astro_rules.aspects import aspect_between
from services.ephemeris.provider import PlanetaryPosition, PlanetaryState
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.resonance.cycles import (
    cycle_contribution_from_aspect,
    cycle_for_pair,
    load_cycle_registry,
)
from services.resonance.episode_clustering import (
    CandidatePoint,
    EpisodeEventProfile,
    ResonanceEpisode,
    cluster_candidate_points,
    select_diverse_episodes,
)
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import build_weekly_index
from services.resonance.index_store import INDEX_STORE_VERSION, load_built_index, save_built_index
from services.resonance.scoring import (
    NarrativeConfidenceBreakdown,
    PlanetaryScoreBreakdown,
    build_resonance_strength_breakdown,
    calibrate_structural_similarity,
    cycle_power_score,
    outer_sign_environment_similarity,
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


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))


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


def test_structural_similarity_requires_outer_epoch_support() -> None:
    query = vectorize_global_slow(
        _state(
            {
                "Jupiter": 74.0,
                "Saturn": 62.0,
                "Uranus": 324.0,
                "Neptune": 309.0,
                "Pluto": 255.0,
            }
        )
    ).vector
    mismatched_epoch = vectorize_global_slow(
        _state(
            {
                "Jupiter": 66.0,
                "Saturn": 87.0,
                "Uranus": 339.0,
                "Neptune": 293.0,
                "Pluto": 243.0,
            }
        )
    ).vector
    matching_outer_epoch = vectorize_global_slow(
        _state(
            {
                "Jupiter": 45.0,
                "Saturn": 42.0,
                "Uranus": 324.0,
                "Neptune": 309.0,
                "Pluto": 255.0,
            }
        )
    ).vector

    assert outer_sign_environment_similarity(query, mismatched_epoch) < 0.72
    assert calibrate_structural_similarity(
        raw_score=0.90,
        query_vector=query,
        candidate_vector=mismatched_epoch,
    ) < 0.82
    assert calibrate_structural_similarity(
        raw_score=0.90,
        query_vector=query,
        candidate_vector=matching_outer_epoch,
    ) == pytest.approx(0.90)


def test_structural_similarity_allows_shared_outer_aspect_evidence() -> None:
    query = vectorize_global_slow(
        _state(
            {
                "Jupiter": 15.0,
                "Saturn": 75.0,
                "Uranus": 300.0,
                "Neptune": 301.0,
                "Pluto": 180.0,
            }
        )
    ).vector
    shared_outer_aspect = vectorize_global_slow(
        _state(
            {
                "Jupiter": 80.0,
                "Saturn": 140.0,
                "Uranus": 0.0,
                "Neptune": 1.0,
                "Pluto": 240.0,
            }
        )
    ).vector

    assert outer_sign_environment_similarity(query, shared_outer_aspect) < 0.72
    assert calibrate_structural_similarity(
        raw_score=0.90,
        query_vector=query,
        candidate_vector=shared_outer_aspect,
    ) == pytest.approx(0.90)


def test_2001_jupiter_pluto_match_does_not_overrate_early_1500s_epoch() -> None:
    if importlib.util.find_spec("swisseph") is None:
        pytest.skip("Swiss Ephemeris is not installed.")

    provider = SwissEphemerisProvider()
    query = vectorize_global_slow(
        provider.compute_state(datetime(2001, 5, 6, 12, tzinfo=UTC))
    ).vector
    early_1500s = vectorize_global_slow(
        provider.compute_state(datetime(1503, 3, 23, 12, tzinfo=UTC))
    ).vector
    matching_outer_epoch = vectorize_global_slow(
        provider.compute_state(datetime(2000, 5, 1, 12, tzinfo=UTC))
    ).vector

    raw_false_positive = _cosine(query, early_1500s)
    calibrated_false_positive = calibrate_structural_similarity(
        raw_score=raw_false_positive,
        query_vector=query,
        candidate_vector=early_1500s,
    )
    raw_matching_epoch = _cosine(query, matching_outer_epoch)

    assert raw_false_positive > 0.86
    assert calibrated_false_positive < 0.82
    assert calibrate_structural_similarity(
        raw_score=raw_matching_epoch,
        query_vector=query,
        candidate_vector=matching_outer_epoch,
    ) == pytest.approx(raw_matching_epoch)


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


def _episode(
    best_date: date,
    score: float,
    *,
    row_index: int = 1,
) -> ResonanceEpisode:
    return ResonanceEpisode(
        period_start=best_date,
        period_end=best_date,
        best_date=best_date,
        best_score=score,
        best_percentile=0.9,
        row_indices=(row_index,),
    )


def test_diversity_selection_suppresses_repeated_early_1500s_peak() -> None:
    cluster_winner = _episode(date(1501, 5, 1), 0.89, row_index=1)
    nearby_1502 = _episode(date(1502, 5, 1), 0.88, row_index=2)
    nearby_1503 = _episode(date(1503, 5, 1), 0.87, row_index=3)
    separate_period = _episode(date(1608, 5, 1), 0.78, row_index=4)

    selected = select_diverse_episodes(
        [nearby_1503, separate_period, cluster_winner, nearby_1502],
        max_episodes=3,
    )

    assert [item.episode.best_date.year for item in selected] == [1501, 1608]
    assert [item.episode.best_date.year for item in selected[0].related_windows] == [
        1502,
        1503,
    ]


def test_diversity_selection_suppresses_shared_1815_1816_event_context() -> None:
    winner_1815 = _episode(date(1815, 6, 1), 0.82, row_index=1)
    duplicate_1816 = _episode(date(1816, 6, 1), 0.80, row_index=2)
    separate_period = _episode(date(1848, 3, 1), 0.72, row_index=3)
    profiles = {
        winner_1815: EpisodeEventProfile(
            event_ids=frozenset({"evt_a", "evt_b", "evt_c"}),
            long_process_event_ids=frozenset({"evt_a"}),
        ),
        duplicate_1816: EpisodeEventProfile(
            event_ids=frozenset({"evt_a", "evt_b", "evt_c"}),
            long_process_event_ids=frozenset({"evt_a"}),
        ),
        separate_period: EpisodeEventProfile(event_ids=frozenset({"evt_x"})),
    }

    selected = select_diverse_episodes(
        [duplicate_1816, separate_period, winner_1815],
        max_episodes=3,
        event_profiles=profiles,
    )

    assert [item.episode.best_date.year for item in selected] == [1815, 1848]
    assert selected[0].related_windows[0].episode.best_date.year == 1816
    assert selected[0].related_windows[0].reason in {
        "same_long_historical_process",
        "nearby_event_overlap_gt_60_percent",
        "within_5_year_cooldown",
    }


def test_diversity_selection_suppresses_nearby_macro_resonance_signature() -> None:
    early_peak = _episode(date(1516, 5, 1), 0.66, row_index=1)
    stronger_macro_peak = _episode(date(1527, 6, 27), 0.80, row_index=2)
    independent_peak = _episode(date(1848, 3, 1), 0.70, row_index=3)
    shared_signature = frozenset(
        {
            "cycle:Neptune-Pluto:sextile",
            "cycle:Neptune-Uranus:sextile",
            "sign_regime:Pluto:Capricorn",
        }
    )
    profiles = {
        early_peak: EpisodeEventProfile(driver_keys=shared_signature),
        stronger_macro_peak: EpisodeEventProfile(driver_keys=shared_signature),
        independent_peak: EpisodeEventProfile(
            driver_keys=frozenset({"cycle:Uranus-Pluto:square"})
        ),
    }

    selected = select_diverse_episodes(
        [early_peak, independent_peak, stronger_macro_peak],
        max_episodes=3,
        event_profiles=profiles,
    )

    assert [item.episode.best_date.year for item in selected] == [1527, 1848]
    assert selected[0].related_windows[0].episode.best_date.year == 1516
    assert selected[0].related_windows[0].reason == "same_macro_resonance_structure"


def test_diversity_selection_keeps_highest_scored_match_in_cluster() -> None:
    lower = _episode(date(2001, 1, 1), 0.81, row_index=1)
    higher = _episode(date(2002, 1, 1), 0.84, row_index=2)

    selected = select_diverse_episodes([lower, higher], max_episodes=2)

    assert selected[0].episode == higher
    assert selected[0].related_windows[0].episode == lower


def test_diversity_selection_does_not_suppress_distant_event_overlap() -> None:
    winner = _episode(date(1920, 1, 1), 0.80, row_index=1)
    duplicate = _episode(date(1940, 1, 1), 0.79, row_index=2)
    profiles = {
        winner: EpisodeEventProfile(event_ids=frozenset({"evt_a", "evt_b"})),
        duplicate: EpisodeEventProfile(event_ids=frozenset({"evt_a", "evt_b"})),
    }

    selected = select_diverse_episodes(
        [winner, duplicate],
        max_episodes=2,
        event_profiles=profiles,
    )

    assert [item.episode.best_date.year for item in selected] == [1920, 1940]


def test_diversity_selection_suppresses_nearby_high_event_overlap() -> None:
    winner = _episode(date(1920, 1, 1), 0.80, row_index=1)
    duplicate = _episode(date(1928, 1, 1), 0.79, row_index=2)
    profiles = {
        winner: EpisodeEventProfile(event_ids=frozenset({"evt_a", "evt_b"})),
        duplicate: EpisodeEventProfile(event_ids=frozenset({"evt_a", "evt_b"})),
    }

    selected = select_diverse_episodes(
        [winner, duplicate],
        max_episodes=2,
        event_profiles=profiles,
    )

    assert [item.episode.best_date.year for item in selected] == [1920]
    assert selected[0].related_windows[0].reason == "nearby_event_overlap_gt_60_percent"


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
