from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    event_sources_from_events,
    load_curated_events,
)
from services.historical.data_bias import (
    build_historical_data_bias_report,
    render_historical_data_bias_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    events = load_curated_events(args.events_csv)
    report = build_historical_data_bias_report(
        events=events,
        sources=event_sources_from_events(events),
    )
    if args.format == "markdown":
        rendered = render_historical_data_bias_markdown(report)
    else:
        rendered = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"output": str(args.output), "warnings": report.warnings},
                ensure_ascii=False,
            )
        )
        return
    print(rendered)


if __name__ == "__main__":
    main()
