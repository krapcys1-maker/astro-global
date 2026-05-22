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

from services.historical.coverage import build_coverage_report
from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    load_curated_events,
    write_events_to_duckdb,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--db", type=Path, default=Path("data/duckdb/astro_global.duckdb"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    events = load_curated_events(args.csv)
    report = build_coverage_report(events)
    payload = {
        "events_loaded": len(events),
        "coverage": report.model_dump(),
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        args.db.parent.mkdir(parents=True, exist_ok=True)
        write_events_to_duckdb(args.db, events)
        payload["db_path"] = str(args.db)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
