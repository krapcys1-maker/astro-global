from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app
from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    load_curated_events,
    write_events_to_duckdb,
)

DEFAULT_OUTPUT = (
    ROOT
    / "tests"
    / "golden"
    / "resonance_compare"
    / "synthetic_2026-05-22T12Z_vs_2020-03-11T00Z.json"
)
DEFAULT_COMPARE_REQUEST = {
    "left_date_utc": "2026-05-22T12:00:00Z",
    "right_date_utc": "2020-03-11T00:00:00Z",
    "lookback_years": 3,
    "lookahead_years": 0,
    "top_k": 20,
    "max_episodes": 3,
    "events_per_episode": 4,
    "event_window_years": 1,
}
GOLDEN_SESSION_TOKEN = "golden-test-token"
GOLDEN_AUTH_HEADERS = {"x-astro-global-session": GOLDEN_SESSION_TOKEN}


def build_resonance_compare_golden(csv_path: Path | str = DEFAULT_CURATED_EVENTS_PATH) -> dict:
    events = load_curated_events(csv_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "astro_global.duckdb"
        write_events_to_duckdb(db_path, events)
        client = TestClient(create_app(event_db_path=db_path, session_token=GOLDEN_SESSION_TOKEN))
        response = client.post(
            "/resonance/compare",
            headers=GOLDEN_AUTH_HEADERS,
            json=DEFAULT_COMPARE_REQUEST,
        )
    response.raise_for_status()
    return response.json()


def serialize(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update or verify the golden /resonance/compare API response."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the existing golden file differs from the generated response.",
    )
    args = parser.parse_args()

    rendered = serialize(build_resonance_compare_golden(args.csv))
    if args.check:
        existing = args.output.read_text(encoding="utf-8")
        if existing != rendered:
            raise SystemExit(
                f"{args.output} is out of date. "
                "Run `python scripts/update_resonance_compare_golden.py`."
            )
        print(f"{args.output} is up to date")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
