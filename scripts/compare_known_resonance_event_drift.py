from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_CURRENT_JSON = ROOT / "work" / "reports" / "known_resonance_cases_1900_now.json"
DEFAULT_JSON_OUTPUT = ROOT / "work" / "reports" / "known_resonance_event_drift.json"
DEFAULT_MD_OUTPUT = ROOT / "work" / "reports" / "known_resonance_event_drift.md"
LONG_PROCESS_KIND = "long_process"


def build_drift_report(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    baseline_label: str,
    current_label: str,
) -> dict[str, Any]:
    baseline_cases = _cases_by_query_date(baseline)
    current_cases = _cases_by_query_date(current)
    compared_dates = sorted(set(baseline_cases) & set(current_cases))
    case_deltas = [
        _case_delta(
            baseline_case=baseline_cases[query_date],
            current_case=current_cases[query_date],
        )
        for query_date in compared_dates
    ]
    warning_count_delta = _counter_delta(
        baseline.get("warning_counts", {}),
        current.get("warning_counts", {}),
    )
    event_mix_warning_count_delta = _counter_delta(
        baseline.get("event_mix_warning_counts", {}),
        current.get("event_mix_warning_counts", {}),
    )
    warning_counts = Counter(
        warning
        for case in case_deltas
        for warning in case["drift_warnings"]
    )
    matched_event_changes = [
        case
        for case in case_deltas
        if case["added_matched_event_ids"] or case["removed_matched_event_ids"]
    ]
    expected_event_regressions = [
        case
        for case in case_deltas
        if case["lost_expected_event_ids"]
    ]
    return {
        "baseline_label": baseline_label,
        "current_label": current_label,
        "cases_compared": len(case_deltas),
        "baseline_only_query_dates": sorted(set(baseline_cases) - set(current_cases)),
        "current_only_query_dates": sorted(set(current_cases) - set(baseline_cases)),
        "matched_event_change_count": len(matched_event_changes),
        "expected_event_regression_count": len(expected_event_regressions),
        "warning_count_delta": warning_count_delta,
        "event_mix_warning_count_delta": event_mix_warning_count_delta,
        "drift_warning_counts": dict(sorted(warning_counts.items())),
        "case_deltas": case_deltas,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Known Resonance Event Drift",
        "",
        f"- Baseline: `{report['baseline_label']}`",
        f"- Current: `{report['current_label']}`",
        f"- Cases compared: {report['cases_compared']}",
        f"- Cases with matched-event changes: {report['matched_event_change_count']}",
        f"- Expected-event regressions: {report['expected_event_regression_count']}",
        f"- Warning count delta: `{json.dumps(report['warning_count_delta'], sort_keys=True)}`",
        "- Event-mix warning count delta: "
        f"`{json.dumps(report['event_mix_warning_count_delta'], sort_keys=True)}`",
        f"- Drift warning counts: `{json.dumps(report['drift_warning_counts'], sort_keys=True)}`",
        "",
    ]
    if report["baseline_only_query_dates"] or report["current_only_query_dates"]:
        lines.extend(
            [
                "## Case Set Changes",
                "",
                "- Baseline-only query dates: "
                f"`{', '.join(report['baseline_only_query_dates']) or 'none'}`",
                "- Current-only query dates: "
                f"`{', '.join(report['current_only_query_dates']) or 'none'}`",
                "",
            ]
        )

    lines.extend(["## Case Deltas", ""])
    for case in report["case_deltas"]:
        lines.extend(_render_case_delta(case))
    return "\n".join(lines).rstrip() + "\n"


def _render_case_delta(case: dict[str, Any]) -> list[str]:
    return [
        f"### {case['query_date']}",
        "",
        "- Added matched events: "
        f"`{', '.join(case['added_matched_event_ids']) or 'none'}`",
        "- Removed matched events: "
        f"`{', '.join(case['removed_matched_event_ids']) or 'none'}`",
        "- Expected events: "
        f"`{', '.join(case['expected_event_ids']) or 'none'}`",
        "- Lost expected events: "
        f"`{', '.join(case['lost_expected_event_ids']) or 'none'}`",
        "- Candidate long-process share: "
        f"`{case['baseline_candidate_long_process_share']:.3f} -> "
        f"{case['current_candidate_long_process_share']:.3f}`",
        "- Selected long-process share: "
        f"`{case['baseline_selected_long_process_share']:.3f} -> "
        f"{case['current_selected_long_process_share']:.3f}`",
        "- Event-mix warnings: "
        f"`{', '.join(case['baseline_event_mix_warnings']) or 'none'} -> "
        f"{', '.join(case['current_event_mix_warnings']) or 'none'}`",
        "- Drift warnings: "
        f"`{', '.join(case['drift_warnings']) or 'none'}`",
        "",
    ]


def _case_delta(*, baseline_case: dict[str, Any], current_case: dict[str, Any]) -> dict[str, Any]:
    baseline_event_ids = _matched_event_ids(baseline_case)
    current_event_ids = _matched_event_ids(current_case)
    expected_event_ids = tuple(current_case["expectation_evaluation"]["expected_event_ids"])
    lost_expected_event_ids = tuple(
        event_id for event_id in expected_event_ids if event_id not in current_event_ids
    )
    baseline_mix = _event_mix_totals(baseline_case)
    current_mix = _event_mix_totals(current_case)
    baseline_event_mix_warnings = _event_mix_warnings(baseline_case)
    current_event_mix_warnings = _event_mix_warnings(current_case)
    added_event_ids = tuple(sorted(set(current_event_ids) - set(baseline_event_ids)))
    removed_event_ids = tuple(sorted(set(baseline_event_ids) - set(current_event_ids)))
    drift_warnings = _drift_warnings(
        added_event_ids=added_event_ids,
        removed_event_ids=removed_event_ids,
        lost_expected_event_ids=lost_expected_event_ids,
        baseline_mix=baseline_mix,
        current_mix=current_mix,
        baseline_event_mix_warnings=baseline_event_mix_warnings,
        current_event_mix_warnings=current_event_mix_warnings,
    )
    return {
        "query_date": current_case["query_date"],
        "baseline_matched_event_ids": baseline_event_ids,
        "current_matched_event_ids": current_event_ids,
        "added_matched_event_ids": added_event_ids,
        "removed_matched_event_ids": removed_event_ids,
        "expected_event_ids": expected_event_ids,
        "lost_expected_event_ids": lost_expected_event_ids,
        "baseline_candidate_long_process_share": baseline_mix["candidate_long_process_share"],
        "current_candidate_long_process_share": current_mix["candidate_long_process_share"],
        "candidate_long_process_share_delta": (
            current_mix["candidate_long_process_share"]
            - baseline_mix["candidate_long_process_share"]
        ),
        "baseline_selected_long_process_share": baseline_mix["selected_long_process_share"],
        "current_selected_long_process_share": current_mix["selected_long_process_share"],
        "selected_long_process_share_delta": (
            current_mix["selected_long_process_share"]
            - baseline_mix["selected_long_process_share"]
        ),
        "baseline_event_mix_warnings": baseline_event_mix_warnings,
        "current_event_mix_warnings": current_event_mix_warnings,
        "drift_warnings": drift_warnings,
    }


def _drift_warnings(
    *,
    added_event_ids: tuple[str, ...],
    removed_event_ids: tuple[str, ...],
    lost_expected_event_ids: tuple[str, ...],
    baseline_mix: dict[str, float],
    current_mix: dict[str, float],
    baseline_event_mix_warnings: tuple[str, ...],
    current_event_mix_warnings: tuple[str, ...],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if added_event_ids or removed_event_ids:
        warnings.append("matched_event_set_changed")
    if removed_event_ids:
        warnings.append("matched_events_removed")
    if lost_expected_event_ids:
        warnings.append("expected_event_regression")
    selected_delta = (
        current_mix["selected_long_process_share"]
        - baseline_mix["selected_long_process_share"]
    )
    candidate_delta = (
        current_mix["candidate_long_process_share"]
        - baseline_mix["candidate_long_process_share"]
    )
    if selected_delta > 0.20:
        warnings.append("selected_long_process_share_increased")
    if candidate_delta > 0.15:
        warnings.append("candidate_long_process_share_increased")
    new_event_mix_warnings = set(current_event_mix_warnings) - set(baseline_event_mix_warnings)
    if new_event_mix_warnings:
        warnings.append("new_event_mix_warning")
    return tuple(warnings)


def _cases_by_query_date(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["query_date"]: case for case in report.get("cases", ())}


def _matched_event_ids(case: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                event["event_id"]
                for episode in case.get("top_episodes", ())
                for event in episode.get("matched_events", ())
            }
        )
    )


def _event_mix_totals(case: dict[str, Any]) -> dict[str, float]:
    candidate_total = 0
    candidate_long_process_count = 0
    selected_total = 0
    selected_long_process_count = 0
    for episode in case.get("top_episodes", ()):
        diagnostic = episode.get("event_mix_diagnostic", {})
        candidate_counts = diagnostic.get("candidate_pool_event_kind_counts", {})
        selected_counts = diagnostic.get("selected_event_kind_counts", {})
        candidate_total += sum(int(count) for count in candidate_counts.values())
        candidate_long_process_count += int(candidate_counts.get(LONG_PROCESS_KIND, 0))
        selected_total += sum(int(count) for count in selected_counts.values())
        selected_long_process_count += int(selected_counts.get(LONG_PROCESS_KIND, 0))
    return {
        "candidate_long_process_share": (
            candidate_long_process_count / candidate_total if candidate_total else 0.0
        ),
        "selected_long_process_share": (
            selected_long_process_count / selected_total if selected_total else 0.0
        ),
    }


def _event_mix_warnings(case: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                warning
                for episode in case.get("top_episodes", ())
                for warning in episode.get("event_mix_diagnostic", {}).get("warnings", ())
            }
        )
    )


def _counter_delta(
    baseline_counts: dict[str, Any],
    current_counts: dict[str, Any],
) -> dict[str, int]:
    keys = set(baseline_counts) | set(current_counts)
    return {
        key: int(current_counts.get(key, 0)) - int(baseline_counts.get(key, 0))
        for key in sorted(keys)
        if int(current_counts.get(key, 0)) != int(baseline_counts.get(key, 0))
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare known-case benchmark reports for matched-event drift."
    )
    parser.add_argument("--baseline-json", type=Path, required=True)
    parser.add_argument("--current-json", type=Path, default=DEFAULT_CURRENT_JSON)
    parser.add_argument("--baseline-label", default=None)
    parser.add_argument("--current-label", default=None)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_drift_report(
        baseline=_load_json(args.baseline_json),
        current=_load_json(args.current_json),
        baseline_label=args.baseline_label or str(args.baseline_json),
        current_label=args.current_label or str(args.current_json),
    )
    rendered_json = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    rendered_md = render_markdown(report)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(rendered_json, encoding="utf-8")
    args.md_output.write_text(rendered_md, encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "cases_compared": report["cases_compared"],
                "matched_event_change_count": report["matched_event_change_count"],
                "expected_event_regression_count": report["expected_event_regression_count"],
                "drift_warning_counts": report["drift_warning_counts"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
