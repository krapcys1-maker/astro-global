from __future__ import annotations

import argparse
import csv
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
    load_curated_events,
    sort_curated_events,
    validate_curated_events_stable_order,
)


def _write_sorted_events(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            msg = f"{csv_path} has no CSV header"
            raise ValueError(msg)
        rows_by_id = {row["id"]: row for row in reader}

    sorted_event_ids = [event.id for event in sort_curated_events(load_curated_events(csv_path))]
    sorted_rows = [rows_by_id[event_id] for event_id in sorted_event_ids]

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    events = load_curated_events(args.events_csv)
    payload = {
        "events_csv": str(args.events_csv),
        "events_loaded": len(events),
        "stable_order": True,
        "fixed": False,
    }
    try:
        validate_curated_events_stable_order(events)
    except ValueError as exc:
        if not args.fix:
            payload["stable_order"] = False
            payload["error"] = str(exc)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            raise SystemExit(1) from exc
        _write_sorted_events(args.events_csv)
        validate_curated_events_stable_order(load_curated_events(args.events_csv))
        payload["fixed"] = True

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
