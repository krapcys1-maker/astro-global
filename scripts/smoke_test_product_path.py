from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID

DEFAULT_INDEX_FILE = "swiss_1900_now_global_slow_v1.npz"
DEFAULT_QUERY_DATE = "2020-01-12T00:00:00Z"
SESSION_TOKEN = "product-smoke-token"
AUTH_HEADERS = {"x-astro-global-session": SESSION_TOKEN}
FORBIDDEN_SUMMARY_PHRASES = (
    "to sie wydarzy",
    "planety spowoduja",
    "przewidujemy",
    "pewne jest",
)


def _parse_datetime(raw: str) -> datetime:
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _event_ids(episodes: list[dict[str, Any]]) -> set[str]:
    return {
        str(event["event_id"])
        for episode in episodes
        for event in episode.get("matched_events", [])
    }


def _run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    index_path = Path(args.vector_index_root) / args.index_file
    _assert(
        index_path.exists(),
        (
            f"Missing Swiss index: {index_path}. Build it with "
            "scripts/build_planetary_index.py before running product smoke."
        ),
    )

    query_dt = _parse_datetime(args.date)
    with tempfile.TemporaryDirectory(prefix="astro-global-product-smoke-") as tmp:
        db_path = Path(tmp) / "astro_global.duckdb"
        write_events_to_duckdb(db_path, load_curated_events())
        client = TestClient(
            create_app(
                event_db_path=db_path,
                vector_index_root=args.vector_index_root,
                session_token=SESSION_TOKEN,
            )
        )
        response = client.post(
            "/resonance/search",
            headers=AUTH_HEADERS,
            json={
                "date_utc": query_dt.isoformat(),
                "profile_id": GLOBAL_SLOW_PROFILE_ID,
                "lookback_years": args.lookback_years,
                "lookahead_years": args.lookahead_years,
                "step_days": args.step_days,
                "top_k": args.top_k,
                "max_episodes": args.max_episodes,
                "events_per_episode": args.events_per_episode,
                "event_window_years": args.event_window_years,
                "provider": "swiss",
                "index_file": args.index_file,
            },
        )

    _assert(response.status_code == 200, f"Product smoke API failed: {response.text}")
    payload = response.json()
    episodes = payload.get("episodes", [])
    first_episode = episodes[0] if episodes else {}
    first_events = first_episode.get("matched_events", [])
    summary = payload.get("deterministic_summary", {})
    summary_text = str(summary.get("summary", "")).lower()
    referenced_event_ids = set(summary.get("referenced_event_ids", []))
    matched_event_ids = _event_ids(episodes)

    _assert(payload["provider"] != "synthetic-dev", "Product smoke used synthetic provider.")
    _assert(payload["index_source"] == "persistent_npz", "Product smoke did not use NPZ index.")
    _assert(payload["index_artifact"] == args.index_file, "Unexpected index artifact.")
    _assert(payload["index_rows"] >= args.min_index_rows, "Too few index rows in search window.")
    _assert(episodes, "No resonance episodes returned.")
    _assert(first_events, "Top episode has no matched events.")
    _assert(
        all(event.get("sources") for event in first_events),
        "At least one top-episode event has no sources.",
    )
    _assert(first_episode["score_breakdown"]["planetary_resonance_score"] > 0.0, "Empty score.")
    _assert(
        first_episode["narrative_confidence"]["narrative_confidence"] > 0.0,
        "Empty narrative confidence.",
    )
    _assert(summary.get("language") == "pl", "Deterministic summary is not Polish.")
    _assert(
        referenced_event_ids <= matched_event_ids,
        "Summary referenced event IDs outside matched events.",
    )
    _assert(
        not any(phrase in summary_text for phrase in FORBIDDEN_SUMMARY_PHRASES),
        "Deterministic summary contains a predictive forbidden phrase.",
    )
    if args.expected_event_id:
        _assert(
            args.expected_event_id in matched_event_ids,
            f"Missing expected event ID: {args.expected_event_id}",
        )

    return {
        "date_utc": payload["query_datetime_utc"],
        "provider": payload["provider"],
        "index_artifact": payload["index_artifact"],
        "index_rows": payload["index_rows"],
        "episodes": len(episodes),
        "top_best_date": first_episode["best_date"],
        "top_label": first_episode["score_breakdown"]["label"],
        "top_events": [event["event_id"] for event in first_events],
        "summary_referenced_event_ids": sorted(referenced_event_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_QUERY_DATE)
    parser.add_argument("--vector-index-root", default=str(ROOT / "data" / "vectors"))
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE)
    parser.add_argument("--lookback-years", type=int, default=120)
    parser.add_argument("--lookahead-years", type=int, default=0)
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--max-episodes", type=int, default=5)
    parser.add_argument("--events-per-episode", type=int, default=6)
    parser.add_argument("--event-window-years", type=int, default=1)
    parser.add_argument("--min-index-rows", type=int, default=1000)
    parser.add_argument("--expected-event-id", default="evt_covid_19_pandemic")
    result = _run_smoke(parser.parse_args())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
