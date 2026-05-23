from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
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
from services.historical.source_health import (
    DEFAULT_TIMEOUT_SECONDS,
    check_source_url_group,
    group_source_urls,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check HTTP health for curated historical source URLs."
    )
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Check only the first N unique URLs; useful for quick smoke checks.",
    )
    parser.add_argument(
        "--include-wikidata",
        action="store_true",
        help="Include generated Wikidata seed URLs in addition to curated source URLs.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of concurrent URL checks.",
    )
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    events = load_curated_events(args.events_csv)
    all_sources = event_sources_from_events(events)
    sources = (
        all_sources
        if args.include_wikidata
        else tuple(source for source in all_sources if source.source_quality != "wikidata_seed")
    )
    groups = group_source_urls(sources)
    if args.limit is not None:
        groups = groups[: args.limit]

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = tuple(
            executor.map(
                lambda group: check_source_url_group(
                    group,
                    timeout_seconds=args.timeout,
                ),
                groups,
            )
        )
    failed = tuple(result for result in results if not result.ok)
    payload = {
        "events_csv": str(args.events_csv),
        "sources_loaded": len(sources),
        "unique_urls_checked": len(results),
        "failed_count": len(failed),
        "failed": [
            {
                "url": result.url,
                "method": result.method,
                "status_code": result.status_code,
                "final_url": result.final_url,
                "error": result.error,
                "source_ids": result.source_ids,
                "event_ids": result.event_ids,
            }
            for result in failed
        ],
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
