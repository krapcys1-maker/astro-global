from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.historical.context import BROAD_CONTEXT_EVENT_IDS
from services.historical.curated_importer import event_sources_from_events, load_curated_events
from services.historical.events import EventSource, HistoricalEvent

DEFAULT_JSON_OUTPUT = ROOT / "work" / "reports" / "reliable_history_1500_1900_coverage.json"
DEFAULT_MD_OUTPUT = ROOT / "work" / "reports" / "reliable_history_1500_1900_coverage.md"
CENTURY_WINDOWS = (
    (1500, 1599),
    (1600, 1699),
    (1700, 1799),
    (1800, 1899),
)
THIN_HISTORY_EVENT_THRESHOLD = 12


def _overlaps(event: HistoricalEvent, start_year: int, end_year: int) -> bool:
    return event.start_astro_year <= end_year and event.end_astro_year >= start_year


def build_reliable_history_coverage_report(
    *,
    events: tuple[HistoricalEvent, ...],
    sources: tuple[EventSource, ...],
    thin_history_event_threshold: int = THIN_HISTORY_EVENT_THRESHOLD,
) -> dict[str, Any]:
    sources_by_event: dict[str, list[EventSource]] = defaultdict(list)
    for source in sources:
        sources_by_event[source.event_id].append(source)

    centuries: list[dict[str, Any]] = []
    for start_year, end_year in CENTURY_WINDOWS:
        century_events = tuple(
            event for event in events if _overlaps(event, start_year, end_year)
        )
        event_ids = {event.id for event in century_events}
        century_sources = tuple(
            source for source in sources if source.event_id in event_ids
        )
        long_process_count = sum(
            1 for event in century_events if event.event_kind == "long_process"
        )
        context_event_count = sum(
            1 for event in century_events if event.id in BROAD_CONTEXT_EVENT_IDS
        )
        event_count = len(century_events)
        warning = "thin_history" if event_count < thin_history_event_threshold else None
        centuries.append(
            {
                "label": f"{start_year}-{end_year}",
                "start_year": start_year,
                "end_year": end_year,
                "event_count": event_count,
                "source_count": len(century_sources),
                "long_process_count": long_process_count,
                "context_event_count": context_event_count,
                "long_process_share": (
                    round(long_process_count / event_count, 4) if event_count else 0.0
                ),
                "context_event_share": (
                    round(context_event_count / event_count, 4) if event_count else 0.0
                ),
                "events_without_sources": sorted(
                    event.id for event in century_events if not sources_by_event.get(event.id)
                ),
                "warning": warning,
                "has_too_little_data": warning is not None,
            }
        )

    return {
        "range_label": "reliable_history_1500_1900",
        "start_year": 1500,
        "end_year": 1899,
        "thin_history_event_threshold": thin_history_event_threshold,
        "centuries": centuries,
        "warnings": [
            century["label"]
            for century in centuries
            if century["warning"] == "thin_history"
        ],
    }


def render_reliable_history_coverage_markdown(report: dict[str, Any]) -> str:
    thin_history_centuries = ", ".join(report["warnings"]) if report["warnings"] else "none"
    lines = [
        "# Reliable History Coverage 1500-1900",
        "",
        f"- Range: `{report['start_year']}-{report['end_year']}`",
        f"- Thin-history threshold: `{report['thin_history_event_threshold']}` events/century",
        f"- Thin-history centuries: `{thin_history_centuries}`",
        "",
        "## Century Coverage",
        "",
        "| Century | Events | Sources | Long Process Share | Context Event Share | Warning |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for century in report["centuries"]:
        lines.append(
            "| {label} | {event_count} | {source_count} | {long_process_share:.1%} | "
            "{context_event_share:.1%} | {warning} |".format(
                label=century["label"],
                event_count=century["event_count"],
                source_count=century["source_count"],
                long_process_share=century["long_process_share"],
                context_event_share=century["context_event_share"],
                warning=century["warning"] or "none",
            )
        )

    lines.extend(["", "## Events Without Sources", ""])
    any_missing = False
    for century in report["centuries"]:
        missing = century["events_without_sources"]
        if not missing:
            continue
        any_missing = True
        lines.append(f"- `{century['label']}`: `{', '.join(missing)}`")
    if not any_missing:
        lines.append("- none")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    events = load_curated_events()
    report = build_reliable_history_coverage_report(
        events=events,
        sources=event_sources_from_events(events),
    )
    if args.format == "markdown":
        rendered = render_reliable_history_coverage_markdown(report)
        output = args.output or DEFAULT_MD_OUTPUT
    else:
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        output = args.output or DEFAULT_JSON_OUTPUT

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "warnings": report["warnings"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
