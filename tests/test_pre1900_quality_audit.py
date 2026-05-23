from __future__ import annotations

from scripts.pre1900_quality_audit import (
    PRE1900_QUALITY_CASES,
    _evaluate_expectations,
    _quality_warnings,
)


def _cases_by_date() -> dict[str, dict]:
    return {case["query_date"]: case for case in PRE1900_QUALITY_CASES}


def test_pre1900_quality_case_set_has_manual_benchmark_depth() -> None:
    cases = _cases_by_date()

    assert len(cases) >= 25
    for query_date in (
        "1517-01-01",
        "1648-10-24",
        "1789-07-14",
        "1848-02-24",
        "1868-01-03",
        "1895-11-08",
    ):
        assert cases[query_date]["regression_required"] is True


def test_pre1900_quality_expectations_pass_for_visible_top_n_event() -> None:
    case = {
        "query_date": "1789-07-14",
        "expected_event_ids": ("evt_french_revolution",),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Uranus"), "aspect": "conjunction", "tier_prefix": "C_"},
        ),
    }
    payload = {
        "primary_cycles": [
            {
                "pair": ("Uranus", "Jupiter"),
                "aspect": "conjunction",
                "tier": "C_activator",
            }
        ],
        "supporting_cycles": [],
    }
    episodes = [
        {
            "period_start": "1789-07-01",
            "period_end": "1789-07-31",
            "matched_events": [{"event_id": "evt_french_revolution"}],
            "context_events": [],
        }
    ]

    evaluation = _evaluate_expectations(case=case, payload=payload, episodes=episodes)

    assert evaluation["missing_expected_event_ids"] == []
    assert evaluation["top_episode_missing_expected_event_ids"] == []
    assert evaluation["missing_expected_cycles"] == []
    assert evaluation["missing_expected_windows"] == []


def test_pre1900_quality_expectations_flag_missing_event_cycle_and_window() -> None:
    case = {
        "query_date": "1848-02-24",
        "expected_event_ids": ("evt_revolutions_1848",),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Saturn"), "aspect": "trine", "tier_prefix": "B_"},
        ),
    }
    payload = {
        "primary_cycles": [],
        "supporting_cycles": [
            {
                "pair": ("Jupiter", "Saturn"),
                "aspect": "square",
                "tier": "B_social_order",
            }
        ],
    }
    episodes = [
        {
            "period_start": "1847-01-01",
            "period_end": "1847-02-01",
            "matched_events": [{"event_id": "evt_other"}],
            "context_events": [],
        }
    ]

    evaluation = _evaluate_expectations(case=case, payload=payload, episodes=episodes)

    assert evaluation["missing_expected_event_ids"] == ["evt_revolutions_1848"]
    assert evaluation["top_episode_missing_expected_event_ids"] == ["evt_revolutions_1848"]
    assert evaluation["missing_expected_cycles"] == ["Jupiter-Saturn trine B_"]
    assert evaluation["missing_expected_windows"] == ["1848-02-24 +/- 14 days"]


def test_pre1900_quality_warnings_surface_expected_failure_modes() -> None:
    payload = {
        "index_coverage": {"index_coverage_status": "partial"},
    }
    episodes = [
        {
            "warnings": ["thin_history"],
            "event_mix_diagnostic": {"warnings": ["long_process_heavy"]},
            "matched_events": [
                {"event_id": "evt_globalization_era"},
            ],
            "narrative_confidence": {"narrative_confidence": 0.4},
            "event_coverage": {"events_found": 1},
        }
    ]
    evaluation = {
        "missing_expected_event_ids": ["evt_expected"],
        "top_episode_missing_expected_event_ids": ["evt_expected"],
        "missing_expected_context_event_ids": ["evt_context"],
        "missing_expected_cycles": ["Saturn-Pluto conjunction A_"],
        "missing_expected_windows": ["expected window"],
    }

    warnings = _quality_warnings(
        payload=payload,
        episodes=episodes,
        evaluation=evaluation,
    )

    assert warnings == [
        "broad_context_displacement",
        "expected_context_not_separated",
        "index_coverage_not_full",
        "long_process_heavy",
        "low_confidence",
        "low_event_coverage",
        "missing_expected_cycles",
        "missing_expected_events",
        "missing_expected_windows",
        "thin_history",
        "top_episode_missing_expected_events",
    ]
