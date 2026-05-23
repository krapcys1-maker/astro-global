from __future__ import annotations

from scripts.benchmark_known_resonance_cases import (
    _build_event_mix_diagnostic,
    _cycle_matches_expectation,
    _episode_warnings,
    _evaluate_case_expectations,
    _has_strong_outer_cycle,
    _jupiter_primary_share,
)
from services.historical.events import HistoricalEvent


def _event(event_id: str, event_kind: str, *, is_ongoing: bool = False) -> HistoricalEvent:
    return HistoricalEvent(
        id=event_id,
        title=event_id,
        display_date="2020-" if is_ongoing else "2020",
        start_astro_year=2020,
        end_astro_year=2026 if is_ongoing else 2020,
        category="test",
        event_kind=event_kind,
        region="Global",
        geo_scope="global",
        source_url="https://www.wikidata.org/wiki/Q1",
        confidence_score=0.5,
        is_ongoing=is_ongoing,
    )


def test_known_case_warning_rules_detect_thin_war_biased_strong_result() -> None:
    episode = {
        "score_breakdown": {"label": "strong"},
        "event_coverage": {
            "events_found": 1,
            "categories": {"war": 1},
        },
        "narrative_confidence": {"narrative_confidence": 0.4},
    }

    warnings = _episode_warnings(
        episode_payload=episode,
        primary_cycles=[
            {
                "pair": ("Jupiter", "Saturn"),
                "tier": "B_social_order",
                "contribution": 0.6,
            }
        ],
    )

    assert warnings == [
        "no_strong_outer_cycle",
        "low_event_coverage",
        "war_bias",
        "thin_history",
    ]


def test_known_case_cycle_diagnostics_track_outer_cycles_and_jupiter_share() -> None:
    primary_cycles = [
        {"pair": ("Saturn", "Uranus"), "tier": "A_structural", "contribution": 0.8},
        {"pair": ("Jupiter", "Saturn"), "tier": "B_social_order", "contribution": 0.2},
    ]

    assert _has_strong_outer_cycle(primary_cycles) is True
    assert _jupiter_primary_share(primary_cycles) == 0.2


def test_known_case_cycle_expectations_match_unordered_planet_pairs() -> None:
    assert _cycle_matches_expectation(
        cycle={
            "pair": ("Pluto", "Saturn"),
            "aspect": "conjunction",
            "tier": "A_structural",
        },
        expected_cycle={
            "pair": ("Saturn", "Pluto"),
            "aspect": "conjunction",
            "tier_prefix": "A_",
        },
    )


def test_known_case_expectations_match_cycles_windows_and_events() -> None:
    expectation = {
        "expected_cycles": [
            {
                "pair": ("Saturn", "Pluto"),
                "aspect": "conjunction",
                "tier_prefix": "A_",
            }
        ],
        "expected_episode_windows": [
            {"label": "query window", "start": "2020-01-01", "end": "2020-02-01"}
        ],
        "expected_event_ids": ("evt_covid_19_pandemic",),
    }

    result = _evaluate_case_expectations(
        expected=expectation,
        primary_cycles=[
            {
                "pair": ("Pluto", "Saturn"),
                "aspect": "conjunction",
                "tier": "A_structural",
            }
        ],
        supporting_cycles=[],
        episode_payloads=[
            {
                "period_start": "2019-12-01",
                "period_end": "2020-03-01",
                "best_date": "2020-01-13",
                "matched_events": [{"event_id": "evt_covid_19_pandemic"}],
            }
        ],
    )

    assert result["passed"] is True
    assert result["missing_expected_cycles"] == []
    assert result["missing_expected_windows"] == []
    assert result["missing_expected_event_ids"] == []


def test_known_case_expectations_report_missing_calibration_targets() -> None:
    expectation = {
        "expected_cycles": [
            {"pair": ("Saturn", "Uranus"), "aspect": "square", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "query window", "start": "2021-01-01", "end": "2021-03-01"}
        ],
        "expected_event_ids": ("evt_expected",),
    }

    result = _evaluate_case_expectations(
        expected=expectation,
        primary_cycles=[],
        supporting_cycles=[],
        episode_payloads=[
            {
                "period_start": "2020-01-01",
                "period_end": "2020-02-01",
                "best_date": "2020-01-15",
                "matched_events": [{"event_id": "evt_other"}],
            }
        ],
    )

    assert result["passed"] is False
    assert result["missing_expected_cycles"] == ["Saturn-Uranus square A_"]
    assert result["missing_expected_windows"] == ["query window"]
    assert result["missing_expected_event_ids"] == ["evt_expected"]


def test_event_mix_diagnostic_detects_possible_long_process_displacement() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {"event_id": "evt_long", "event_kind": "long_process", "is_ongoing": False},
            {"event_id": "evt_long_2", "event_kind": "long_process", "is_ongoing": False},
            {"event_id": "evt_crisis", "event_kind": "crisis", "is_ongoing": False},
        ],
        candidate_events=[
            _event("evt_long", "long_process"),
            _event("evt_long_2", "long_process"),
            _event("evt_crisis", "crisis"),
            _event("evt_omitted_point", "instant_event"),
        ],
        requested_event_limit=3,
    )

    assert diagnostic["selected_long_process_share"] == 2 / 3
    assert diagnostic["omitted_point_event_ids"] == ("evt_omitted_point",)
    assert diagnostic["hidden_point_event_ids"] == ("evt_omitted_point",)
    assert diagnostic["warnings"] == [
        "long_process_heavy",
        "point_events_beyond_limit",
        "possible_long_process_displacement",
    ]


def test_event_mix_diagnostic_treats_overflow_point_events_as_visible() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {"event_id": "evt_long", "event_kind": "long_process", "is_ongoing": False},
            {"event_id": "evt_long_2", "event_kind": "long_process", "is_ongoing": False},
            {"event_id": "evt_crisis", "event_kind": "crisis", "is_ongoing": False},
        ],
        overflow_point_events=[
            {"event_id": "evt_omitted_point", "event_kind": "instant_event", "is_ongoing": False}
        ],
        candidate_events=[
            _event("evt_long", "long_process"),
            _event("evt_long_2", "long_process"),
            _event("evt_crisis", "crisis"),
            _event("evt_omitted_point", "instant_event"),
        ],
        requested_event_limit=3,
    )

    assert diagnostic["omitted_point_event_ids"] == ("evt_omitted_point",)
    assert diagnostic["overflow_point_event_ids"] == ("evt_omitted_point",)
    assert diagnostic["hidden_point_event_ids"] == ()
    assert diagnostic["warnings"] == ["long_process_heavy"]


def test_event_mix_diagnostic_flags_long_process_boundary_share() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {"event_id": "evt_long", "event_kind": "long_process", "is_ongoing": False},
            {"event_id": "evt_crisis", "event_kind": "crisis", "is_ongoing": False},
        ],
        candidate_events=[
            _event("evt_long", "long_process"),
            _event("evt_crisis", "crisis"),
        ],
        requested_event_limit=2,
    )

    assert diagnostic["selected_long_process_share"] == 0.5
    assert diagnostic["warnings"] == ["long_process_heavy"]


def test_event_mix_diagnostic_flags_broad_context_watchlist() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {
                "event_id": "evt_globalization_era",
                "event_kind": "long_process",
                "is_ongoing": False,
            },
            {"event_id": "evt_crisis", "event_kind": "crisis", "is_ongoing": False},
        ],
        candidate_events=[
            _event("evt_globalization_era", "long_process"),
            _event("evt_crisis", "crisis"),
        ],
        requested_event_limit=2,
    )

    assert diagnostic["selected_broad_context_ids"] == ("evt_globalization_era",)
    assert diagnostic["warnings"] == [
        "long_process_heavy",
        "broad_context_watchlist",
    ]


def test_event_mix_diagnostic_tracks_separated_context_events() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {"event_id": "evt_crisis", "event_kind": "crisis", "is_ongoing": False},
        ],
        context_events=[
            {
                "event_id": "evt_globalization_era",
                "event_kind": "long_process",
                "is_ongoing": False,
            },
        ],
        candidate_events=[
            _event("evt_globalization_era", "long_process"),
            _event("evt_crisis", "crisis"),
        ],
        requested_event_limit=2,
    )

    assert diagnostic["context_event_ids"] == ("evt_globalization_era",)
    assert diagnostic["selected_broad_context_ids"] == ()
    assert diagnostic["warnings"] == []


def test_event_mix_diagnostic_detects_ongoing_heavy_results() -> None:
    diagnostic = _build_event_mix_diagnostic(
        selected_events=[
            {"event_id": "evt_a", "event_kind": "war", "is_ongoing": True},
            {"event_id": "evt_b", "event_kind": "crisis", "is_ongoing": True},
            {"event_id": "evt_c", "event_kind": "instant_event", "is_ongoing": False},
        ],
        candidate_events=[
            _event("evt_a", "war", is_ongoing=True),
            _event("evt_b", "crisis", is_ongoing=True),
            _event("evt_c", "instant_event"),
        ],
        requested_event_limit=3,
    )

    assert diagnostic["selected_ongoing_share"] == 2 / 3
    assert diagnostic["warnings"] == ["ongoing_heavy"]
