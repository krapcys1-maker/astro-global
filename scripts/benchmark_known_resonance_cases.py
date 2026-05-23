from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import DEFAULT_VECTOR_INDEX_ROOT, _episode_response
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.historical.event_query import DEFAULT_DUCKDB_PATH, find_events_overlapping_years
from services.historical.events import HistoricalEvent
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.index_store import load_built_index
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID, vectorize_global_slow

KNOWN_CASE_DATES = (
    "2020-01-12",
    "2020-12-21",
    "2021-02-17",
    "1989-03-03",
    "1965-10-09",
    "2008-09-15",
    "1914-07-28",
    "1939-09-01",
    "1968-05-01",
    "1989-11-09",
)
DEFAULT_INDEX_FILE = "swiss_1900_now_global_slow_v1.npz"
DEFAULT_JSON_OUTPUT = ROOT / "work" / "reports" / "known_resonance_cases_1900_now.json"
DEFAULT_MD_OUTPUT = ROOT / "work" / "reports" / "known_resonance_cases_1900_now.md"
DEFAULT_EVENT_DIAGNOSTIC_POOL_LIMIT = 25
POINT_EVENT_KINDS = frozenset({"instant_event", "short_event", "crisis", "institution"})
LONG_PROCESS_EVENT_KIND = "long_process"
LONG_PROCESS_HEAVY_THRESHOLD = 0.5
ONGOING_HEAVY_THRESHOLD = 0.5

KNOWN_CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "2020-01-12": {
        "expected_cycles": [
            {"pair": ("Saturn", "Pluto"), "aspect": "conjunction", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "Saturn-Pluto 2020 window", "start": "2019-11-01", "end": "2020-05-15"}
        ],
        "expected_event_ids": ("evt_covid_19_pandemic",),
    },
    "2020-12-21": {
        "expected_cycles": [
            {"pair": ("Jupiter", "Saturn"), "aspect": "conjunction", "tier_prefix": "B_"}
        ],
        "expected_episode_windows": [
            {"label": "Jupiter-Saturn 2020 window", "start": "2020-10-01", "end": "2021-06-01"}
        ],
        "expected_event_ids": ("evt_covid_19_pandemic",),
    },
    "2021-02-17": {
        "expected_cycles": [
            {"pair": ("Saturn", "Uranus"), "aspect": "square", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "Saturn-Uranus 2021 window", "start": "2020-12-01", "end": "2021-09-01"}
        ],
        "expected_event_ids": ("evt_covid_19_pandemic",),
    },
    "1989-03-03": {
        "expected_cycles": [
            {"pair": ("Saturn", "Neptune"), "aspect": "conjunction", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "Saturn-Neptune 1989 window", "start": "1988-12-01", "end": "1989-09-01"}
        ],
        "expected_event_ids": ("evt_fall_berlin_wall", "evt_tiananmen_1989"),
    },
    "1965-10-09": {
        "expected_cycles": [
            {"pair": ("Uranus", "Pluto"), "aspect": "conjunction", "tier_prefix": "S_"}
        ],
        "expected_episode_windows": [
            {"label": "Uranus-Pluto 1965 window", "start": "1965-07-01", "end": "1966-02-01"}
        ],
        "expected_event_ids": (
            "evt_cultural_revolution",
            "evt_vietnam_war",
            "evt_green_revolution",
        ),
    },
    "2008-09-15": {
        "expected_cycles": [
            {"pair": ("Jupiter", "Saturn"), "aspect": "trine", "tier_prefix": "B_"}
        ],
        "expected_episode_windows": [
            {"label": "Financial crisis 2008 window", "start": "2008-06-01", "end": "2009-01-01"}
        ],
        "expected_event_ids": ("evt_financial_crisis_2007_2008",),
    },
    "1914-07-28": {
        "expected_cycles": [
            {"pair": ("Saturn", "Pluto"), "aspect": "conjunction", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "World War I 1914 window", "start": "1914-05-01", "end": "1915-02-01"}
        ],
        "expected_event_ids": ("evt_world_war_i",),
    },
    "1939-09-01": {
        "expected_cycles": [
            {"pair": ("Saturn", "Pluto"), "aspect": "square", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "World War II 1939 window", "start": "1939-05-01", "end": "1939-12-01"}
        ],
        "expected_event_ids": ("evt_world_war_ii", "evt_great_depression"),
    },
    "1968-05-01": {
        "expected_cycles": [
            {"pair": ("Jupiter", "Neptune"), "aspect": "square", "tier_prefix": "C_"},
            {"pair": ("Uranus", "Neptune"), "aspect": "sextile", "tier_prefix": "S_"},
        ],
        "expected_episode_windows": [
            {"label": "1968 unrest window", "start": "1968-01-01", "end": "1968-08-01"}
        ],
        "expected_event_ids": ("evt_cultural_revolution", "evt_vietnam_war"),
    },
    "1989-11-09": {
        "expected_cycles": [
            {"pair": ("Saturn", "Neptune"), "aspect": "conjunction", "tier_prefix": "A_"}
        ],
        "expected_episode_windows": [
            {"label": "Berlin Wall 1989 window", "start": "1989-07-01", "end": "1990-05-01"}
        ],
        "expected_event_ids": (
            "evt_fall_berlin_wall",
            "evt_soviet_dissolution",
            "evt_tiananmen_1989",
        ),
    },
}


def _parse_case_datetime(raw_date: str) -> str:
    return f"{raw_date}T00:00:00+00:00"


def _has_strong_outer_cycle(primary_cycles: list[dict[str, Any]]) -> bool:
    return any(str(cycle.get("tier", "")).startswith(("S_", "A_")) for cycle in primary_cycles)


def _jupiter_primary_share(primary_cycles: list[dict[str, Any]]) -> float:
    total = sum(float(cycle.get("contribution", 0.0)) for cycle in primary_cycles)
    if total <= 0.0:
        return 0.0
    jupiter = sum(
        float(cycle.get("contribution", 0.0))
        for cycle in primary_cycles
        if "Jupiter" in tuple(cycle.get("pair", ()))
    )
    return jupiter / total


def _canonical_pair(pair: Any) -> tuple[str, ...]:
    return tuple(sorted(str(item) for item in pair))


def _expected_cycle_label(expected_cycle: dict[str, Any]) -> str:
    pair = "-".join(str(item) for item in expected_cycle["pair"])
    return f"{pair} {expected_cycle.get('aspect', '*')} {expected_cycle.get('tier_prefix', '')}"


def _cycle_matches_expectation(
    *,
    cycle: dict[str, Any],
    expected_cycle: dict[str, Any],
) -> bool:
    if _canonical_pair(cycle.get("pair", ())) != _canonical_pair(expected_cycle["pair"]):
        return False
    expected_aspect = expected_cycle.get("aspect")
    if expected_aspect and cycle.get("aspect") != expected_aspect:
        return False
    expected_tier_prefix = expected_cycle.get("tier_prefix")
    if expected_tier_prefix and not str(cycle.get("tier", "")).startswith(expected_tier_prefix):
        return False
    return True


def _episode_overlaps_window(
    *,
    episode_payload: dict[str, Any],
    expected_window: dict[str, Any],
) -> bool:
    episode_start = date.fromisoformat(episode_payload["period_start"])
    episode_end = date.fromisoformat(episode_payload["period_end"])
    expected_start = date.fromisoformat(expected_window["start"])
    expected_end = date.fromisoformat(expected_window["end"])
    return episode_start <= expected_end and episode_end >= expected_start


def _evaluate_case_expectations(
    *,
    expected: dict[str, Any] | None,
    primary_cycles: list[dict[str, Any]],
    supporting_cycles: list[dict[str, Any]],
    episode_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    if expected is None:
        return {
            "configured": False,
            "passed": True,
            "summary": "no_expectations_configured",
            "cycles": [],
            "episode_windows": [],
            "expected_event_ids": [],
            "matched_event_ids": [],
            "missing_expected_event_ids": [],
            "missing_expected_cycles": [],
            "missing_expected_windows": [],
        }

    all_cycles = list(primary_cycles) + list(supporting_cycles)
    cycle_results = []
    missing_cycles = []
    for expected_cycle in expected.get("expected_cycles", ()):
        matched_cycle = next(
            (
                cycle
                for cycle in all_cycles
                if _cycle_matches_expectation(cycle=cycle, expected_cycle=expected_cycle)
            ),
            None,
        )
        label = _expected_cycle_label(expected_cycle)
        if matched_cycle is None:
            missing_cycles.append(label)
        cycle_results.append(
            {
                "label": label,
                "matched": matched_cycle is not None,
                "matched_cycle": matched_cycle,
            }
        )

    window_results = []
    missing_windows = []
    for expected_window in expected.get("expected_episode_windows", ()):
        matched_episode = next(
            (
                episode
                for episode in episode_payloads
                if _episode_overlaps_window(
                    episode_payload=episode,
                    expected_window=expected_window,
                )
            ),
            None,
        )
        if matched_episode is None:
            missing_windows.append(expected_window["label"])
        window_results.append(
            {
                "label": expected_window["label"],
                "start": expected_window["start"],
                "end": expected_window["end"],
                "matched": matched_episode is not None,
                "matched_episode_best_date": (
                    matched_episode["best_date"] if matched_episode else None
                ),
            }
        )

    matched_event_ids = sorted(
        {
            event["event_id"]
            for episode in episode_payloads
            for event in episode.get("matched_events", ())
        }
    )
    expected_event_ids = sorted(
        str(event_id) for event_id in expected.get("expected_event_ids", ())
    )
    missing_event_ids = sorted(set(expected_event_ids) - set(matched_event_ids))
    passed = not missing_cycles and not missing_windows and not missing_event_ids

    return {
        "configured": True,
        "passed": passed,
        "summary": "passed" if passed else "missing_expectations",
        "cycles": cycle_results,
        "episode_windows": window_results,
        "expected_event_ids": expected_event_ids,
        "matched_event_ids": matched_event_ids,
        "missing_expected_event_ids": missing_event_ids,
        "missing_expected_cycles": missing_cycles,
        "missing_expected_windows": missing_windows,
    }


def _episode_warnings(
    *,
    episode_payload: dict[str, Any],
    primary_cycles: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    score = episode_payload["score_breakdown"]
    coverage = episode_payload["event_coverage"]
    confidence = episode_payload["narrative_confidence"]
    events_found = int(coverage["events_found"])
    has_outer = _has_strong_outer_cycle(primary_cycles)

    if score["label"] == "strong" and not has_outer:
        warnings.append("no_strong_outer_cycle")
    if events_found < 3:
        warnings.append("low_event_coverage")
    if events_found:
        war_count = int(coverage["categories"].get("war", 0))
        if war_count / events_found >= 0.5:
            warnings.append("war_bias")
    if events_found < 2 or float(confidence["narrative_confidence"]) < 0.5:
        warnings.append("thin_history")
    return warnings


def _event_id(event: dict[str, Any] | HistoricalEvent) -> str:
    if isinstance(event, dict):
        return str(event["event_id"])
    return event.id


def _event_kind(event: dict[str, Any] | HistoricalEvent) -> str:
    if isinstance(event, dict):
        return str(event["event_kind"])
    return event.event_kind


def _event_is_ongoing(event: dict[str, Any] | HistoricalEvent) -> bool:
    if isinstance(event, dict):
        return bool(event.get("is_ongoing", False))
    return event.is_ongoing


def _event_kind_counts(events: Sequence[dict[str, Any] | HistoricalEvent]) -> dict[str, int]:
    return dict(sorted(Counter(_event_kind(event) for event in events).items()))


def _build_event_mix_diagnostic(
    *,
    selected_events: Sequence[dict[str, Any]],
    candidate_events: Sequence[HistoricalEvent],
    requested_event_limit: int,
    overflow_point_events: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    selected_tuple = tuple(selected_events)
    overflow_point_tuple = tuple(overflow_point_events)
    candidate_tuple = tuple(candidate_events)
    selected_ids = {_event_id(event) for event in selected_tuple}
    overflow_point_ids = tuple(_event_id(event) for event in overflow_point_tuple)
    visible_ids = selected_ids | set(overflow_point_ids)
    omitted_candidates = tuple(
        event for event in candidate_tuple if _event_id(event) not in selected_ids
    )
    hidden_candidates = tuple(
        event for event in candidate_tuple if _event_id(event) not in visible_ids
    )
    selected_long_process_ids = tuple(
        _event_id(event)
        for event in selected_tuple
        if _event_kind(event) == LONG_PROCESS_EVENT_KIND
    )
    selected_point_event_ids = tuple(
        _event_id(event)
        for event in selected_tuple
        if _event_kind(event) in POINT_EVENT_KINDS
    )
    omitted_point_event_ids = tuple(
        _event_id(event)
        for event in omitted_candidates
        if _event_kind(event) in POINT_EVENT_KINDS
    )
    hidden_point_event_ids = tuple(
        _event_id(event)
        for event in hidden_candidates
        if _event_kind(event) in POINT_EVENT_KINDS
    )
    selected_ongoing_ids = tuple(
        _event_id(event) for event in selected_tuple if _event_is_ongoing(event)
    )
    selected_count = len(selected_tuple)
    selected_long_process_share = (
        len(selected_long_process_ids) / selected_count if selected_count else 0.0
    )
    selected_point_event_share = (
        len(selected_point_event_ids) / selected_count if selected_count else 0.0
    )
    selected_ongoing_share = len(selected_ongoing_ids) / selected_count if selected_count else 0.0

    warnings: list[str] = []
    if selected_long_process_share > LONG_PROCESS_HEAVY_THRESHOLD:
        warnings.append("long_process_heavy")
    if selected_ongoing_share >= ONGOING_HEAVY_THRESHOLD:
        warnings.append("ongoing_heavy")
    if hidden_point_event_ids:
        warnings.append("point_events_beyond_limit")
    if selected_long_process_ids and hidden_point_event_ids:
        warnings.append("possible_long_process_displacement")

    return {
        "requested_event_limit": requested_event_limit,
        "candidate_pool_size": len(candidate_tuple),
        "selected_event_kind_counts": _event_kind_counts(selected_tuple),
        "candidate_pool_event_kind_counts": _event_kind_counts(candidate_tuple),
        "selected_long_process_ids": selected_long_process_ids,
        "selected_point_event_ids": selected_point_event_ids,
        "selected_ongoing_ids": selected_ongoing_ids,
        "omitted_point_event_ids": omitted_point_event_ids,
        "overflow_point_event_ids": overflow_point_ids,
        "hidden_point_event_ids": hidden_point_event_ids,
        "selected_long_process_share": selected_long_process_share,
        "selected_point_event_share": selected_point_event_share,
        "selected_ongoing_share": selected_ongoing_share,
        "warnings": warnings,
    }


def _case_report(
    *,
    query_date: str,
    provider: SwissEphemerisProvider,
    index_path: Path,
    index_artifact: str,
    event_db_path: Path,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
    event_diagnostic_pool_limit: int,
) -> dict[str, Any]:
    built_index, metadata = load_built_index(index_path)
    query_state = provider.compute_state(query_date_to_datetime(query_date))
    query_vector = vectorize_global_slow(query_state)
    hits = exact_search(built_index.matrix, query_vector.vector, top_k=top_k)
    points = [
        CandidatePoint(
            date=built_index.rows[hit.row_index].datetime_utc.date(),
            score=hit.score,
            row_index=hit.row_index,
            percentile=hit.percentile,
        )
        for hit in hits
    ]
    episodes = cluster_candidate_points(points)[:max_episodes]
    primary_cycles = query_vector.cycle_strength_debug_json["primary_cycles"]
    supporting_cycles = query_vector.cycle_strength_debug_json["supporting_cycles"]

    episode_payloads: list[dict[str, Any]] = []
    all_warnings: set[str] = set()
    for episode in episodes:
        response = _episode_response(
            episode=episode,
            event_db_path=event_db_path,
            event_window_years=event_window_years,
            events_per_episode=events_per_episode,
            index_rows=len(built_index.rows),
            primary_cycles=primary_cycles,
        )
        payload = response.model_dump()
        candidate_events = find_events_overlapping_years(
            start_astro_year=episode.period_start.year - event_window_years,
            end_astro_year=episode.period_end.year + event_window_years,
            db_path=event_db_path,
            limit=event_diagnostic_pool_limit,
        )
        payload["event_mix_diagnostic"] = _build_event_mix_diagnostic(
            selected_events=payload["matched_events"],
            candidate_events=candidate_events,
            requested_event_limit=events_per_episode,
            overflow_point_events=payload.get("omitted_point_events", ()),
        )
        warnings = _episode_warnings(episode_payload=payload, primary_cycles=primary_cycles)
        payload["warnings"] = warnings
        all_warnings.update(warnings)
        episode_payloads.append(payload)

    expectation_evaluation = _evaluate_case_expectations(
        expected=KNOWN_CASE_EXPECTATIONS.get(query_date),
        primary_cycles=primary_cycles,
        supporting_cycles=supporting_cycles,
        episode_payloads=episode_payloads,
    )

    return {
        "query_date": query_date,
        "provider": query_state.ephemeris_version,
        "index_artifact": index_artifact,
        "index_metadata": {
            "provider": metadata.get("provider"),
            "rows": metadata.get("rows") and len(metadata["rows"]),
            "step_days": metadata.get("step_days"),
            "profile_id": metadata.get("profile_id"),
            "vector_version": metadata.get("vector_version"),
        },
        "primary_cycles": primary_cycles,
        "supporting_cycles": supporting_cycles,
        "top_episodes": episode_payloads,
        "warnings": sorted(all_warnings),
        "expectation_evaluation": expectation_evaluation,
        "diagnostics": {
            "has_tier_a_or_s_primary_cycle": _has_strong_outer_cycle(primary_cycles),
            "jupiter_primary_contribution_share": round(
                _jupiter_primary_share(primary_cycles), 6
            ),
            "top_episode_count": len(episode_payloads),
        },
    }


def query_date_to_datetime(raw_date: str) -> Any:
    from datetime import datetime

    return datetime.fromisoformat(_parse_case_datetime(raw_date))


def build_report(
    *,
    index_path: Path,
    index_artifact: str,
    event_db_path: Path,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
    event_diagnostic_pool_limit: int,
) -> dict[str, Any]:
    provider = SwissEphemerisProvider()
    cases = [
        _case_report(
            query_date=query_date,
            provider=provider,
            index_path=index_path,
            index_artifact=index_artifact,
            event_db_path=event_db_path,
            top_k=top_k,
            max_episodes=max_episodes,
            events_per_episode=events_per_episode,
            event_window_years=event_window_years,
            event_diagnostic_pool_limit=event_diagnostic_pool_limit,
        )
        for query_date in KNOWN_CASE_DATES
    ]
    warning_counts: dict[str, int] = {}
    for case in cases:
        for warning in case["warnings"]:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
    event_mix_warning_counts: dict[str, int] = {}
    for case in cases:
        for episode in case["top_episodes"]:
            for warning in episode["event_mix_diagnostic"]["warnings"]:
                event_mix_warning_counts[warning] = event_mix_warning_counts.get(warning, 0) + 1
    evaluated_cases = [
        case for case in cases if case["expectation_evaluation"]["configured"]
    ]
    passed_expectations = [
        case for case in evaluated_cases if case["expectation_evaluation"]["passed"]
    ]
    missing_expected_event_ids = {
        case["query_date"]: case["expectation_evaluation"]["missing_expected_event_ids"]
        for case in evaluated_cases
        if case["expectation_evaluation"]["missing_expected_event_ids"]
    }
    missing_expected_cycles = {
        case["query_date"]: case["expectation_evaluation"]["missing_expected_cycles"]
        for case in evaluated_cases
        if case["expectation_evaluation"]["missing_expected_cycles"]
    }
    missing_expected_windows = {
        case["query_date"]: case["expectation_evaluation"]["missing_expected_windows"]
        for case in evaluated_cases
        if case["expectation_evaluation"]["missing_expected_windows"]
    }
    return {
        "profile_id": GLOBAL_SLOW_PROFILE_ID,
        "index_artifact": index_artifact,
        "cases_count": len(cases),
        "warning_counts": dict(sorted(warning_counts.items())),
        "event_mix_warning_counts": dict(sorted(event_mix_warning_counts.items())),
        "expectation_summary": {
            "cases_evaluated": len(evaluated_cases),
            "cases_passed": len(passed_expectations),
            "missing_expected_event_ids": missing_expected_event_ids,
            "missing_expected_cycles": missing_expected_cycles,
            "missing_expected_windows": missing_expected_windows,
        },
        "cases": cases,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Known Resonance Cases - Swiss 1900-now",
        "",
        f"- Profile: `{report['profile_id']}`",
        f"- Index: `{report['index_artifact']}`",
        f"- Cases: {report['cases_count']}",
        f"- Warning counts: `{json.dumps(report['warning_counts'], sort_keys=True)}`",
        "- Event mix warning counts: "
        f"`{json.dumps(report['event_mix_warning_counts'], sort_keys=True)}`",
        "- Calibration expectations: "
        f"`{report['expectation_summary']['cases_passed']}/"
        f"{report['expectation_summary']['cases_evaluated']} passed`",
        "",
    ]
    for case in report["cases"]:
        lines.extend(_render_case_markdown(case))
    return "\n".join(lines).rstrip() + "\n"


def _render_case_markdown(case: dict[str, Any]) -> list[str]:
    lines = [
        f"## {case['query_date']}",
        "",
        f"- Provider: `{case['provider']}`",
        f"- Index artifact: `{case['index_artifact']}`",
        f"- Warnings: `{', '.join(case['warnings']) if case['warnings'] else 'none'}`",
        f"- Has tier A/S primary cycle: `{case['diagnostics']['has_tier_a_or_s_primary_cycle']}`",
        "- Jupiter primary contribution share: "
        f"`{case['diagnostics']['jupiter_primary_contribution_share']}`",
        "",
        "### Primary Cycles",
        "",
    ]
    lines.extend(_render_cycles(case["primary_cycles"]))
    lines.extend(["", "### Supporting Cycles", ""])
    lines.extend(_render_cycles(case["supporting_cycles"][:8]))
    lines.extend(["", "### Calibration Expectations", ""])
    lines.extend(_render_expectation_evaluation(case["expectation_evaluation"]))
    lines.extend(["", "### Top Episodes", ""])
    for idx, episode in enumerate(case["top_episodes"], start=1):
        event_labels = [
            f"{event['event_id']} ({event['display_date']})"
            for event in episode["matched_events"]
        ]
        lines.extend(
            [
                f"#### {idx}. {episode['best_date']}",
                "",
                f"- Period: `{episode['period_start']}..{episode['period_end']}`",
                f"- Score: `{episode['best_score']:.6f}`",
                f"- Percentile: `{episode['best_percentile']:.6f}`",
                f"- Score breakdown: `{json.dumps(episode['score_breakdown'], sort_keys=True)}`",
                f"- Event coverage: `{json.dumps(episode['event_coverage'], sort_keys=True)}`",
                "- Narrative confidence: "
                f"`{json.dumps(episode['narrative_confidence'], sort_keys=True)}`",
                f"- Event mix: `{json.dumps(episode['event_mix_diagnostic'], sort_keys=True)}`",
                f"- Matched events: `{'; '.join(event_labels) if event_labels else 'none'}`",
                f"- Warnings: "
                f"`{', '.join(episode['warnings']) if episode['warnings'] else 'none'}`",
                "",
            ]
        )
    return lines


def _render_expectation_evaluation(expectation: dict[str, Any]) -> list[str]:
    if not expectation["configured"]:
        return ["- none configured"]
    lines = [
        f"- Status: `{'passed' if expectation['passed'] else 'missing_expectations'}`",
        "- Expected cycles: "
        + (
            "; ".join(
                f"{cycle['label']} -> {'matched' if cycle['matched'] else 'missing'}"
                for cycle in expectation["cycles"]
            )
            or "none"
        ),
        "- Expected windows: "
        + (
            "; ".join(
                f"{window['label']} ({window['start']}..{window['end']}) -> "
                f"{window['matched_episode_best_date'] or 'missing'}"
                for window in expectation["episode_windows"]
            )
            or "none"
        ),
        "- Expected event IDs: "
        + (
            ", ".join(expectation["expected_event_ids"])
            if expectation["expected_event_ids"]
            else "none"
        ),
    ]
    missing = (
        expectation["missing_expected_cycles"]
        + expectation["missing_expected_windows"]
        + expectation["missing_expected_event_ids"]
    )
    lines.append(f"- Missing: `{', '.join(missing) if missing else 'none'}`")
    return lines


def _render_cycles(cycles: list[dict[str, Any]]) -> list[str]:
    if not cycles:
        return ["- none"]
    return [
        "- "
        + ", ".join(
            (
                f"pair={tuple(cycle.get('pair', ())) }",
                f"aspect={cycle.get('aspect')}",
                f"tier={cycle.get('tier')}",
                f"orb={float(cycle.get('orb_deg', 0.0)):.3f}",
                f"contribution={float(cycle.get('contribution', 0.0)):.3f}",
            )
        )
        for cycle in cycles
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--index-file",
        default=DEFAULT_INDEX_FILE,
        help="Index filename inside data/vectors or an explicit path.",
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--top-k", type=int, default=80)
    parser.add_argument("--max-episodes", type=int, default=5)
    parser.add_argument("--events-per-episode", type=int, default=6)
    parser.add_argument("--event-window-years", type=int, default=1)
    parser.add_argument(
        "--event-diagnostic-pool-limit",
        type=int,
        default=DEFAULT_EVENT_DIAGNOSTIC_POOL_LIMIT,
    )
    args = parser.parse_args()

    requested_index = Path(args.index_file)
    index_path = (
        requested_index
        if requested_index.is_absolute() or requested_index.parent != Path(".")
        else DEFAULT_VECTOR_INDEX_ROOT / requested_index
    )
    report = build_report(
        index_path=index_path,
        index_artifact=index_path.name,
        event_db_path=DEFAULT_DUCKDB_PATH,
        top_k=args.top_k,
        max_episodes=args.max_episodes,
        events_per_episode=args.events_per_episode,
        event_window_years=args.event_window_years,
        event_diagnostic_pool_limit=args.event_diagnostic_pool_limit,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "cases_count": report["cases_count"],
                "expectation_summary": report["expectation_summary"],
                "event_mix_warning_counts": report["event_mix_warning_counts"],
                "warning_counts": report["warning_counts"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
