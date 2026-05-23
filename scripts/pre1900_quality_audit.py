from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.benchmark_known_resonance_cases import (  # noqa: E402
    _build_event_mix_diagnostic,
    _cycle_matches_expectation,
    _episode_warnings,
)
from services.api.app import create_app  # noqa: E402
from services.historical.context import BROAD_CONTEXT_EVENT_IDS  # noqa: E402
from services.historical.event_query import (  # noqa: E402
    DEFAULT_DUCKDB_PATH,
    find_events_overlapping_years,
)

DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"
DEFAULT_JSON_OUTPUT = ROOT / "work" / "reports" / "pre1900_quality_audit.json"
DEFAULT_MD_OUTPUT = ROOT / "work" / "reports" / "pre1900_quality_audit.md"
SESSION_TOKEN = "quality-audit-token"
AUTH_HEADERS = {"x-astro-global-session": SESSION_TOKEN}
DEFAULT_TOP_K = 80
DEFAULT_MAX_EPISODES = 5
DEFAULT_EVENTS_PER_EPISODE = 6
DEFAULT_EVENT_WINDOW_YEARS = 1
DEFAULT_EXPECTED_WINDOW_DAYS = 14

PRE1900_QUALITY_CASES: tuple[dict[str, Any], ...] = (
    {
        "query_date": "1501-01-01",
        "label": "Atlantic slave trade reliable-start boundary",
        "expected_event_ids": ("evt_atlantic_slave_trade",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1517-01-01",
        "label": "Protestant Reformation",
        "expected_event_ids": ("evt_protestant_reformation",),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Saturn"), "aspect": "trine", "tier_prefix": "B_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1543-01-01",
        "label": "Scientific Revolution",
        "expected_event_ids": ("evt_scientific_revolution",),
        "expected_cycle_drivers": (),
        "root_cause_review": (
            "Fixed: event existed but was ranked behind already-running long background; "
            "boundary-aware long-process sorting now surfaces it."
        ),
    },
    {
        "query_date": "1582-10-15",
        "label": "Gregorian calendar introduction",
        "expected_event_ids": ("evt_gregorian_calendar",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1618-05-23",
        "label": "Thirty Years' War opening",
        "expected_event_ids": ("evt_thirty_years_war",),
        "expected_cycle_drivers": (),
        "root_cause_review": (
            "Fixed: event existed but its start boundary was penalized against older "
            "ongoing processes in the episode window."
        ),
    },
    {
        "query_date": "1648-10-24",
        "label": "Peace of Westphalia / 1648 settlement",
        "expected_event_ids": ("evt_thirty_years_war", "evt_eighty_years_war"),
        "expected_cycle_drivers": (
            {"pair": ("Neptune", "Pluto"), "aspect": "opposition", "tier_prefix": "S_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1660-11-28",
        "label": "Royal Society founding",
        "expected_event_ids": ("evt_royal_society_founding",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1688-11-05",
        "label": "Glorious Revolution",
        "expected_event_ids": ("evt_glorious_revolution",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1694-07-27",
        "label": "Bank of England founding",
        "expected_event_ids": ("evt_bank_of_england_founding",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1756-05-17",
        "label": "Seven Years' War",
        "expected_event_ids": ("evt_seven_years_war",),
        "expected_cycle_drivers": (
            {"pair": ("Pluto", "Uranus"), "aspect": "square", "tier_prefix": "S_"},
        ),
    },
    {
        "query_date": "1776-07-04",
        "label": "American Revolution",
        "expected_event_ids": ("evt_american_revolution",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1787-09-17",
        "label": "United States Constitution",
        "expected_event_ids": ("evt_us_constitution",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1789-07-14",
        "label": "French Revolution",
        "expected_event_ids": ("evt_french_revolution",),
        "expected_context_event_ids": ("evt_enlightenment",),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Uranus"), "aspect": "conjunction", "tier_prefix": "C_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1791-08-22",
        "label": "Haitian Revolution",
        "expected_event_ids": ("evt_haitian_revolution",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1796-05-14",
        "label": "Smallpox vaccine",
        "expected_event_ids": ("evt_smallpox_vaccine",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1804-01-01",
        "label": "Napoleonic Wars / Sokoto boundary",
        "expected_event_ids": ("evt_napoleonic_wars", "evt_sokoto_jihad_start"),
        "expected_cycle_drivers": (),
        "regression_required": True,
        "root_cause_review": (
            "Fixed by data model: keep evt_sokoto_caliphate as broad long_process/context, "
            "and use evt_sokoto_jihad_start as the 1804 point/start marker."
        ),
    },
    {
        "query_date": "1814-09-18",
        "label": "Congress of Vienna",
        "expected_event_ids": ("evt_congress_of_vienna",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1821-03-25",
        "label": "Greek War of Independence",
        "expected_event_ids": ("evt_greek_war_independence",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1830-07-05",
        "label": "French conquest of Algeria",
        "expected_event_ids": ("evt_invasion_algiers_1830",),
        "expected_cycle_drivers": (),
        "regression_required": True,
        "root_cause_review": (
            "Fixed by data model: keep evt_french_conquest_algeria as broad long_process/context, "
            "and use evt_invasion_algiers_1830 as the 1830 point/start marker."
        ),
    },
    {
        "query_date": "1848-02-24",
        "label": "Revolutions of 1848",
        "expected_event_ids": ("evt_revolutions_1848", "evt_communist_manifesto"),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Saturn"), "aspect": "trine", "tier_prefix": "B_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1859-11-24",
        "label": "Origin of Species",
        "expected_event_ids": ("evt_origin_of_species",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1861-04-12",
        "label": "American Civil War",
        "expected_event_ids": ("evt_american_civil_war",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1868-01-03",
        "label": "Meiji Restoration",
        "expected_event_ids": ("evt_meiji_restoration",),
        "expected_cycle_drivers": (
            {"pair": ("Neptune", "Uranus"), "aspect": "square", "tier_prefix": "S_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1869-11-17",
        "label": "Periodic table / Suez Canal opening",
        "expected_event_ids": ("evt_periodic_table", "evt_suez_canal_opening"),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1870-07-19",
        "label": "Franco-Prussian War",
        "expected_event_ids": ("evt_franco_prussian_war",),
        "expected_cycle_drivers": (),
    },
    {
        "query_date": "1884-11-15",
        "label": "Berlin Conference / Sino-French War",
        "expected_event_ids": ("evt_berlin_conference", "evt_sino_french_war"),
        "expected_cycle_drivers": (),
        "root_cause_review": (
            "Fixed: event existed but was displaced by older colonial/global background; "
            "boundary-aware long-process sorting now keeps it visible."
        ),
    },
    {
        "query_date": "1895-11-08",
        "label": "1895 science and imperial wars",
        "expected_event_ids": (
            "evt_xray_discovery",
            "evt_first_sino_japanese_war",
            "evt_first_italo_ethiopian_war",
        ),
        "expected_cycle_drivers": (
            {"pair": ("Jupiter", "Saturn"), "aspect": "square", "tier_prefix": "B_"},
        ),
        "regression_required": True,
    },
    {
        "query_date": "1898-04-21",
        "label": "Spanish-American War",
        "expected_event_ids": ("evt_spanish_american_war",),
        "expected_cycle_drivers": (),
    },
)

NEGATIVE_QUALITY_CASES: tuple[dict[str, Any], ...] = (
    {
        "query_date": "1492-01-01",
        "label": "pre reliable-history request",
        "expected_status": 400,
        "expected_detail_contains": "no rows inside request window",
    },
)


def build_report(
    *,
    index_file: str,
    event_db_path: Path,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
) -> dict[str, Any]:
    client = TestClient(create_app(event_db_path=event_db_path, session_token=SESSION_TOKEN))
    cases = [
        _case_report(
            client=client,
            case=case,
            index_file=index_file,
            event_db_path=event_db_path,
            top_k=top_k,
            max_episodes=max_episodes,
            events_per_episode=events_per_episode,
            event_window_years=event_window_years,
        )
        for case in PRE1900_QUALITY_CASES
    ]
    negative_cases = [
        _negative_case_report(
            client=client,
            case=case,
            index_file=index_file,
            top_k=top_k,
            max_episodes=max_episodes,
            events_per_episode=events_per_episode,
            event_window_years=event_window_years,
        )
        for case in NEGATIVE_QUALITY_CASES
    ]
    warning_counts = Counter(
        warning for case in cases for warning in case["quality_warnings"]
    )
    event_mix_warning_counts = Counter(
        warning
        for case in cases
        for episode in case.get("top_episodes", ())
        for warning in episode.get("event_mix_diagnostic", {}).get("warnings", ())
    )
    regression_cases = [case for case in cases if case["regression_required"]]
    regression_failures = [
        case for case in regression_cases if case["regression_status"] != "passed"
    ]
    missing_expected_event_cases = [
        case
        for case in cases
        if case["expectation_evaluation"]["missing_expected_event_ids"]
    ]
    missing_expected_cycle_cases = [
        case
        for case in cases
        if case["expectation_evaluation"]["missing_expected_cycles"]
    ]
    top_episode_missing_cases = [
        case
        for case in cases
        if case["expectation_evaluation"]["top_episode_missing_expected_event_ids"]
    ]
    negative_failures = [
        case for case in negative_cases if case["negative_status"] != "passed"
    ]
    return {
        "profile_id": "global_slow_v1",
        "index_artifact": index_file,
        "cases_count": len(cases),
        "negative_cases_count": len(negative_cases),
        "top_k": top_k,
        "max_episodes": max_episodes,
        "events_per_episode": events_per_episode,
        "event_window_years": event_window_years,
        "summary": {
            "regression_cases": len(regression_cases),
            "regression_failures": [
                _case_brief(case) for case in regression_failures
            ],
            "missing_expected_event_cases": [
                _case_brief(case) for case in missing_expected_event_cases
            ],
            "missing_expected_cycle_cases": [
                _case_brief(case) for case in missing_expected_cycle_cases
            ],
            "top_episode_missing_expected_event_cases": [
                _case_brief(case) for case in top_episode_missing_cases
            ],
            "negative_failures": [
                _negative_case_brief(case) for case in negative_failures
            ],
            "warning_counts": dict(sorted(warning_counts.items())),
            "event_mix_warning_counts": dict(sorted(event_mix_warning_counts.items())),
        },
        "cases": cases,
        "negative_cases": negative_cases,
    }


def _case_report(
    *,
    client: TestClient,
    case: dict[str, Any],
    index_file: str,
    event_db_path: Path,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
) -> dict[str, Any]:
    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json=_search_payload(
            query_date=case["query_date"],
            index_file=index_file,
            top_k=top_k,
            max_episodes=max_episodes,
            events_per_episode=events_per_episode,
            event_window_years=event_window_years,
        ),
    )
    if response.status_code != 200:
        return _failed_case_report(case=case, response=response)
    payload = response.json()
    episodes = [
        _episode_quality(
            episode=episode,
            primary_cycles=payload["primary_cycles"],
            event_db_path=event_db_path,
            event_window_years=event_window_years,
            events_per_episode=events_per_episode,
        )
        for episode in payload["episodes"]
    ]
    evaluation = _evaluate_expectations(
        case=case,
        payload=payload,
        episodes=episodes,
    )
    quality_warnings = _quality_warnings(
        payload=payload,
        episodes=episodes,
        evaluation=evaluation,
    )
    regression_required = bool(case.get("regression_required", False))
    regression_status = (
        "passed"
        if not regression_required
        or (
            not evaluation["missing_expected_event_ids"]
            and not evaluation["missing_expected_cycles"]
            and not evaluation["missing_expected_windows"]
        )
        else "failed"
    )
    return {
        "query_date": case["query_date"],
        "label": case["label"],
        "regression_required": regression_required,
        "regression_status": regression_status,
        "response_status": response.status_code,
        "index_coverage": payload["index_coverage"],
        "provider": payload["provider"],
        "index_artifact": payload["index_artifact"],
        "primary_cycles": payload["primary_cycles"],
        "supporting_cycles": payload["supporting_cycles"],
        "top_episodes": episodes,
        "expectation_evaluation": evaluation,
        "quality_warnings": quality_warnings,
        "root_cause_review": case.get("root_cause_review", ""),
        "manual_audit": _manual_audit_note(evaluation=evaluation, warnings=quality_warnings),
    }


def _failed_case_report(*, case: dict[str, Any], response: Any) -> dict[str, Any]:
    detail = _response_detail(response)
    warning = "api_request_failed"
    regression_required = bool(case.get("regression_required", False))
    return {
        "query_date": case["query_date"],
        "label": case["label"],
        "regression_required": regression_required,
        "regression_status": "failed" if regression_required else "not_required",
        "response_status": response.status_code,
        "response_detail": detail,
        "index_coverage": None,
        "provider": None,
        "index_artifact": None,
        "primary_cycles": [],
        "supporting_cycles": [],
        "top_episodes": [],
        "expectation_evaluation": {
            "expected_event_ids": list(case.get("expected_event_ids", ())),
            "expected_context_event_ids": list(case.get("expected_context_event_ids", ())),
            "missing_expected_event_ids": list(case.get("expected_event_ids", ())),
            "missing_expected_context_event_ids": list(
                case.get("expected_context_event_ids", ())
            ),
            "top_episode_missing_expected_event_ids": list(
                case.get("expected_event_ids", ())
            ),
            "missing_expected_cycles": [
                _cycle_label(cycle)
                for cycle in case.get("expected_cycle_drivers", ())
            ],
            "missing_expected_windows": [_expected_window(case)["label"]],
            "matched_event_ids_top_n": [],
            "context_event_ids_top_n": [],
            "top_episode_matched_event_ids": [],
            "top_episode_context_event_ids": [],
        },
        "quality_warnings": [warning],
        "manual_audit": f"needs_review: {detail}",
    }


def _negative_case_report(
    *,
    client: TestClient,
    case: dict[str, Any],
    index_file: str,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
) -> dict[str, Any]:
    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json=_search_payload(
            query_date=case["query_date"],
            index_file=index_file,
            top_k=top_k,
            max_episodes=max_episodes,
            events_per_episode=events_per_episode,
            event_window_years=event_window_years,
        ),
    )
    detail = _response_detail(response)
    expected_status = int(case["expected_status"])
    expected_detail = str(case["expected_detail_contains"])
    passed = response.status_code == expected_status and expected_detail in detail
    return {
        "query_date": case["query_date"],
        "label": case["label"],
        "response_status": response.status_code,
        "response_detail": detail,
        "expected_status": expected_status,
        "expected_detail_contains": expected_detail,
        "negative_status": "passed" if passed else "failed",
    }


def _episode_quality(
    *,
    episode: dict[str, Any],
    primary_cycles: list[dict[str, Any]],
    event_db_path: Path,
    event_window_years: int,
    events_per_episode: int,
) -> dict[str, Any]:
    candidate_events = find_events_overlapping_years(
        start_astro_year=date.fromisoformat(episode["period_start"]).year
        - event_window_years,
        end_astro_year=date.fromisoformat(episode["period_end"]).year
        + event_window_years,
        db_path=event_db_path,
        limit=25,
    )
    enriched = dict(episode)
    enriched["event_mix_diagnostic"] = _build_event_mix_diagnostic(
        selected_events=enriched["matched_events"],
        context_events=enriched.get("context_events", ()),
        candidate_events=candidate_events,
        requested_event_limit=events_per_episode,
        overflow_point_events=enriched.get("omitted_point_events", ()),
    )
    enriched["warnings"] = _episode_warnings(
        episode_payload=enriched,
        primary_cycles=primary_cycles,
    )
    return enriched


def _evaluate_expectations(
    *,
    case: dict[str, Any],
    payload: dict[str, Any],
    episodes: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_event_ids = tuple(case.get("expected_event_ids", ()))
    expected_context_event_ids = tuple(case.get("expected_context_event_ids", ()))
    expected_cycles = tuple(case.get("expected_cycle_drivers", ()))
    matched_event_ids = _visible_event_ids(episodes, field="matched_events")
    context_event_ids = _visible_event_ids(episodes, field="context_events")
    all_visible_event_ids = tuple(dict.fromkeys((*matched_event_ids, *context_event_ids)))
    top_episode = episodes[0] if episodes else {}
    top_matched_event_ids = tuple(
        event["event_id"] for event in top_episode.get("matched_events", ())
    )
    top_context_event_ids = tuple(
        event["event_id"] for event in top_episode.get("context_events", ())
    )
    top_visible_event_ids = tuple(dict.fromkeys((*top_matched_event_ids, *top_context_event_ids)))
    all_cycles = [*payload.get("primary_cycles", ()), *payload.get("supporting_cycles", ())]
    missing_cycles = [
        _cycle_label(expected_cycle)
        for expected_cycle in expected_cycles
        if not any(
            _cycle_matches_expectation(cycle=cycle, expected_cycle=expected_cycle)
            for cycle in all_cycles
        )
    ]
    expected_window = _expected_window(case)
    missing_windows = (
        []
        if any(_episode_overlaps_window(episode, expected_window) for episode in episodes)
        else [expected_window["label"]]
    )
    return {
        "expected_event_ids": list(expected_event_ids),
        "expected_context_event_ids": list(expected_context_event_ids),
        "expected_cycle_drivers": [_cycle_label(cycle) for cycle in expected_cycles],
        "expected_window": expected_window,
        "matched_event_ids_top_n": list(matched_event_ids),
        "context_event_ids_top_n": list(context_event_ids),
        "top_episode_matched_event_ids": list(top_matched_event_ids),
        "top_episode_context_event_ids": list(top_context_event_ids),
        "missing_expected_event_ids": [
            event_id
            for event_id in expected_event_ids
            if event_id not in all_visible_event_ids
        ],
        "missing_expected_context_event_ids": [
            event_id
            for event_id in expected_context_event_ids
            if event_id not in context_event_ids
        ],
        "top_episode_missing_expected_event_ids": [
            event_id
            for event_id in expected_event_ids
            if event_id not in top_visible_event_ids
        ],
        "missing_expected_cycles": missing_cycles,
        "missing_expected_windows": missing_windows,
    }


def _quality_warnings(
    *,
    payload: dict[str, Any],
    episodes: list[dict[str, Any]],
    evaluation: dict[str, Any],
) -> list[str]:
    warnings: set[str] = set()
    if payload["index_coverage"]["index_coverage_status"] != "full":
        warnings.add("index_coverage_not_full")
    if evaluation["missing_expected_event_ids"]:
        warnings.add("missing_expected_events")
    if evaluation["top_episode_missing_expected_event_ids"]:
        warnings.add("top_episode_missing_expected_events")
    if evaluation["missing_expected_context_event_ids"]:
        warnings.add("expected_context_not_separated")
    if evaluation["missing_expected_cycles"]:
        warnings.add("missing_expected_cycles")
    if evaluation["missing_expected_windows"]:
        warnings.add("missing_expected_windows")
    for episode in episodes:
        warnings.update(episode.get("warnings", ()))
        warnings.update(episode["event_mix_diagnostic"].get("warnings", ()))
        matched_ids = {
            event["event_id"] for event in episode.get("matched_events", ())
        }
        if matched_ids & BROAD_CONTEXT_EVENT_IDS:
            warnings.add("broad_context_displacement")
        confidence = episode["narrative_confidence"]["narrative_confidence"]
        if confidence < 0.55:
            warnings.add("low_confidence")
        if episode["event_coverage"]["events_found"] < 3:
            warnings.add("low_event_coverage")
    return sorted(warnings)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Pre-1900 Quality Audit",
        "",
        f"- Profile: `{report['profile_id']}`",
        f"- Index: `{report['index_artifact']}`",
        f"- Cases: {report['cases_count']}",
        f"- Negative cases: {report['negative_cases_count']}",
        f"- Regression cases: {summary['regression_cases']}",
        f"- Regression failures: {len(summary['regression_failures'])}",
        "- Missing expected event cases: "
        f"{len(summary['missing_expected_event_cases'])}",
        "- Missing expected cycle cases: "
        f"{len(summary['missing_expected_cycle_cases'])}",
        "- Top episode missing expected event cases: "
        f"{len(summary['top_episode_missing_expected_event_cases'])}",
        f"- Warning counts: `{json.dumps(summary['warning_counts'], sort_keys=True)}`",
        "- Event-mix warning counts: "
        f"`{json.dumps(summary['event_mix_warning_counts'], sort_keys=True)}`",
        "",
        "## Findings To Review",
        "",
    ]
    findings = summary["missing_expected_event_cases"]
    if findings:
        for finding in findings:
            lines.append(
                "- "
                f"{finding['query_date']} `{finding['label']}` missing "
                f"`{', '.join(finding['missing_expected_event_ids'])}`"
            )
    else:
        lines.append("- No missing expected events in the configured top-N audit.")
    lines.extend(["", "## Negative Cases", ""])
    for case in report["negative_cases"]:
        lines.extend(
            [
                f"### {case['query_date']} - {case['label']}",
                "",
                f"- Status: `{case['negative_status']}`",
                f"- Response: `{case['response_status']}`",
                f"- Detail: `{case['response_detail']}`",
                "",
            ]
        )
    lines.extend(["## Cases", ""])
    for case in report["cases"]:
        lines.extend(_render_case_markdown(case))
    return "\n".join(lines).rstrip() + "\n"


def _render_case_markdown(case: dict[str, Any]) -> list[str]:
    evaluation = case["expectation_evaluation"]
    coverage = case["index_coverage"] or {}
    lines = [
        f"### {case['query_date']} - {case['label']}",
        "",
        f"- Regression: `{case['regression_status']}`",
        f"- Coverage: `{coverage.get('index_coverage_status', 'n/a')}`",
        f"- Warnings: `{', '.join(case['quality_warnings']) or 'none'}`",
        "- Expected events: "
        f"`{', '.join(evaluation['expected_event_ids']) or 'none'}`",
        "- Missing expected events: "
        f"`{', '.join(evaluation['missing_expected_event_ids']) or 'none'}`",
        "- Top episode missing expected events: "
        f"`{', '.join(evaluation['top_episode_missing_expected_event_ids']) or 'none'}`",
        "- Expected context events: "
        f"`{', '.join(evaluation['expected_context_event_ids']) or 'none'}`",
        "- Missing expected context events: "
        f"`{', '.join(evaluation['missing_expected_context_event_ids']) or 'none'}`",
        "- Expected cycles: "
        f"`{', '.join(evaluation['expected_cycle_drivers']) or 'none'}`",
        "- Missing expected cycles: "
        f"`{', '.join(evaluation['missing_expected_cycles']) or 'none'}`",
        f"- Manual audit: {case['manual_audit']}",
        f"- Root-cause review: {case.get('root_cause_review') or 'none'}",
        "",
        "#### Top Episodes",
        "",
    ]
    for idx, episode in enumerate(case["top_episodes"], start=1):
        matched = [event["event_id"] for event in episode["matched_events"]]
        context = [event["event_id"] for event in episode.get("context_events", ())]
        lines.extend(
            [
                f"{idx}. `{episode['best_date']}` "
                f"period `{episode['period_start']}..{episode['period_end']}`",
                f"   - matched: `{', '.join(matched) or 'none'}`",
                f"   - context: `{', '.join(context) or 'none'}`",
                "   - event mix warnings: "
                f"`{', '.join(episode['event_mix_diagnostic']['warnings']) or 'none'}`",
                f"   - episode warnings: `{', '.join(episode['warnings']) or 'none'}`",
            ]
        )
    lines.append("")
    return lines


def _manual_audit_note(*, evaluation: dict[str, Any], warnings: list[str]) -> str:
    if evaluation["missing_expected_event_ids"]:
        return "needs_review: expected event missing from top-N visible events"
    if "broad_context_displacement" in warnings:
        return "needs_review: broad context appeared as matched event"
    if evaluation["missing_expected_context_event_ids"]:
        return "needs_review: expected context was not separated"
    if "thin_history" in warnings or "low_confidence" in warnings:
        return "needs_review: confidence or coverage is weak"
    return "sensible_top_n"


def _search_payload(
    *,
    query_date: str,
    index_file: str,
    top_k: int,
    max_episodes: int,
    events_per_episode: int,
    event_window_years: int,
) -> dict[str, Any]:
    return {
        "date_utc": f"{query_date}T00:00:00Z",
        "profile_id": "global_slow_v1",
        "lookback_years": 120,
        "lookahead_years": 0,
        "step_days": 7,
        "top_k": top_k,
        "max_episodes": max_episodes,
        "events_per_episode": events_per_episode,
        "event_window_years": event_window_years,
        "provider": "swiss",
        "index_file": index_file,
    }


def _visible_event_ids(episodes: list[dict[str, Any]], *, field: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            event["event_id"]
            for episode in episodes
            for event in episode.get(field, ())
        )
    )


def _expected_window(case: dict[str, Any]) -> dict[str, str]:
    configured = case.get("expected_window")
    if configured:
        return configured
    center = date.fromisoformat(case["query_date"])
    start = center - timedelta(days=DEFAULT_EXPECTED_WINDOW_DAYS)
    end = center + timedelta(days=DEFAULT_EXPECTED_WINDOW_DAYS)
    return {
        "label": f"{case['query_date']} +/- {DEFAULT_EXPECTED_WINDOW_DAYS} days",
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _episode_overlaps_window(
    episode: dict[str, Any],
    expected_window: dict[str, str],
) -> bool:
    episode_start = date.fromisoformat(episode["period_start"])
    episode_end = date.fromisoformat(episode["period_end"])
    expected_start = date.fromisoformat(expected_window["start"])
    expected_end = date.fromisoformat(expected_window["end"])
    return episode_start <= expected_end and episode_end >= expected_start


def _cycle_label(cycle: dict[str, Any]) -> str:
    pair = "-".join(str(part) for part in cycle["pair"])
    return f"{pair} {cycle.get('aspect', '*')} {cycle.get('tier_prefix', '')}".strip()


def _case_brief(case: dict[str, Any]) -> dict[str, Any]:
    evaluation = case["expectation_evaluation"]
    return {
        "query_date": case["query_date"],
        "label": case["label"],
        "missing_expected_event_ids": evaluation["missing_expected_event_ids"],
        "missing_expected_cycles": evaluation["missing_expected_cycles"],
        "missing_expected_windows": evaluation["missing_expected_windows"],
    }


def _negative_case_brief(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_date": case["query_date"],
        "label": case["label"],
        "response_status": case["response_status"],
        "response_detail": case["response_detail"],
    }


def _response_detail(response: Any) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text
    detail = payload.get("detail", payload)
    return detail if isinstance(detail, str) else json.dumps(detail, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a manual-quality benchmark over pre-1900 curated cases."
    )
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--max-episodes", type=int, default=DEFAULT_MAX_EPISODES)
    parser.add_argument("--events-per-episode", type=int, default=DEFAULT_EVENTS_PER_EPISODE)
    parser.add_argument("--event-window-years", type=int, default=DEFAULT_EVENT_WINDOW_YEARS)
    parser.add_argument(
        "--check-regressions",
        action="store_true",
        help="Exit non-zero when regression_required cases lose configured expectations.",
    )
    args = parser.parse_args()

    report = build_report(
        index_file=args.index_file,
        event_db_path=DEFAULT_DUCKDB_PATH,
        top_k=args.top_k,
        max_episodes=args.max_episodes,
        events_per_episode=args.events_per_episode,
        event_window_years=args.event_window_years,
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
                "negative_cases_count": report["negative_cases_count"],
                "regression_failures": report["summary"]["regression_failures"],
                "missing_expected_event_cases": report["summary"][
                    "missing_expected_event_cases"
                ],
                "warning_counts": report["summary"]["warning_counts"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.check_regressions and report["summary"]["regression_failures"]:
        raise SystemExit("Pre-1900 quality regression check failed.")


if __name__ == "__main__":
    main()
