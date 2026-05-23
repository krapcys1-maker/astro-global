from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app

DEFAULT_OUTPUT = ROOT / "tests" / "golden" / "timeline" / "seeds_swiss_1500_now.json"
GOLDEN_SESSION_TOKEN = "golden-test-token"
GOLDEN_AUTH_HEADERS = {"x-astro-global-session": GOLDEN_SESSION_TOKEN}


def build_timeline_seeds_golden() -> dict:
    client = TestClient(create_app(session_token=GOLDEN_SESSION_TOKEN))
    response = client.get(
        "/timeline/seeds",
        headers=GOLDEN_AUTH_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def serialize(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update or verify the golden /timeline/seeds API response."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the existing golden file differs from the generated response.",
    )
    args = parser.parse_args()

    rendered = serialize(build_timeline_seeds_golden())
    if args.check:
        existing = args.output.read_text(encoding="utf-8")
        if existing != rendered:
            raise SystemExit(
                f"{args.output} is out of date. "
                "Run `python scripts/update_timeline_seeds_golden.py`."
            )
        print(f"{args.output} is up to date")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
