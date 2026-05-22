from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import build_weekly_index
from services.resonance.vectorizer import vectorize_global_slow


def _parse_date(raw: str) -> datetime:
    if raw == "now":
        return datetime.now(tz=UTC).replace(microsecond=0)
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="now")
    parser.add_argument("--profile", default="global_slow_v1")
    args = parser.parse_args()
    if args.profile != "global_slow_v1":
        raise SystemExit("Only global_slow_v1 is available in the backend proof.")

    provider = SyntheticEphemerisProvider()
    query_dt = _parse_date(args.date)
    start = query_dt - timedelta(days=365 * 10)
    end = query_dt + timedelta(days=365 * 2)
    built = build_weekly_index(provider, start, end)
    query_state = provider.compute_state(query_dt)
    query_vector = vectorize_global_slow(query_state)
    hits = exact_search(built.matrix, query_vector.vector, top_k=20)
    points = [
        CandidatePoint(
            date=built.rows[hit.row_index].datetime_utc.date(),
            score=hit.score,
            row_index=hit.row_index,
            percentile=hit.percentile,
        )
        for hit in hits
    ]
    episodes = cluster_candidate_points(points)
    payload = {
        "current_state": {
            "datetime_utc": query_state.datetime_utc.isoformat(),
            "ephemeris_version": query_state.ephemeris_version,
        },
        "primary_cycles": query_vector.cycle_strength_debug_json["primary_cycles"],
        "supporting_cycles": query_vector.cycle_strength_debug_json["supporting_cycles"],
        "episodes": [
            {
                "period_start": episode.period_start.isoformat(),
                "period_end": episode.period_end.isoformat(),
                "best_date": episode.best_date.isoformat(),
                "best_score": episode.best_score,
                "best_percentile": episode.best_percentile,
            }
            for episode in episodes[:8]
        ],
        "summary": "Smoke test pipeline działa na deterministycznym providerze syntetycznym.",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
