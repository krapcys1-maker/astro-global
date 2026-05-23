from __future__ import annotations

from scripts.benchmark_known_resonance_cases import (
    _episode_warnings,
    _has_strong_outer_cycle,
    _jupiter_primary_share,
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
