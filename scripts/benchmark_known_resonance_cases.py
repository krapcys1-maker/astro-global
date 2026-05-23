from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import DEFAULT_VECTOR_INDEX_ROOT, _episode_response
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.historical.event_query import DEFAULT_DUCKDB_PATH
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
        warnings = _episode_warnings(episode_payload=payload, primary_cycles=primary_cycles)
        payload["warnings"] = warnings
        all_warnings.update(warnings)
        episode_payloads.append(payload)

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
        )
        for query_date in KNOWN_CASE_DATES
    ]
    warning_counts: dict[str, int] = {}
    for case in cases:
        for warning in case["warnings"]:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
    return {
        "profile_id": GLOBAL_SLOW_PROFILE_ID,
        "index_artifact": index_artifact,
        "cases_count": len(cases),
        "warning_counts": dict(sorted(warning_counts.items())),
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
                f"- Matched events: `{'; '.join(event_labels) if event_labels else 'none'}`",
                f"- Warnings: "
                f"`{', '.join(episode['warnings']) if episode['warnings'] else 'none'}`",
                "",
            ]
        )
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
                "warning_counts": report["warning_counts"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
