from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.build_planetary_index import PROVIDER_LABELS, build_provider, parse_utc
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import build_weekly_index
from services.resonance.vectorizer import (
    GLOBAL_SLOW_PROFILE_ID,
    GLOBAL_SLOW_VECTOR_VERSION,
    vectorize_global_slow,
)


@dataclass(frozen=True)
class IndexBenchmarkReport:
    provider: str
    profile_id: str
    vector_version: str
    start_utc: str
    end_utc: str
    query_utc: str
    step_days: int
    rows: int
    dimensions: int
    matrix_mb: float
    build_seconds: float
    search_seconds: float
    top_k: int
    top_score: float | None
    top_percentile: float | None
    top_datetime_utc: str | None


def benchmark_index(
    *,
    provider_name: str,
    start_utc: datetime,
    end_utc: datetime,
    query_utc: datetime,
    step_days: int,
    top_k: int,
    ephemeris_path: Path | None = None,
) -> IndexBenchmarkReport:
    if end_utc < start_utc:
        raise ValueError("end_utc must be >= start_utc")
    if step_days < 1:
        raise ValueError("step_days must be >= 1")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    provider = build_provider(provider_name, ephemeris_path)
    provider_label = PROVIDER_LABELS[provider_name]

    build_started = perf_counter()
    built = build_weekly_index(provider, start_utc, end_utc, step_days=step_days)
    build_seconds = perf_counter() - build_started

    query_state = provider.compute_state(query_utc)
    query_vector = vectorize_global_slow(query_state).vector

    search_started = perf_counter()
    hits = exact_search(built.matrix, query_vector, top_k=top_k)
    search_seconds = perf_counter() - search_started

    top_hit = hits[0] if hits else None
    top_row = built.rows[top_hit.row_index] if top_hit is not None else None
    dimensions = int(built.matrix.shape[1]) if built.matrix.ndim == 2 and built.matrix.size else 0

    return IndexBenchmarkReport(
        provider=provider_label,
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        start_utc=start_utc.isoformat(),
        end_utc=end_utc.isoformat(),
        query_utc=query_utc.isoformat(),
        step_days=step_days,
        rows=len(built.rows),
        dimensions=dimensions,
        matrix_mb=round(float(built.matrix.nbytes / 1_048_576), 4),
        build_seconds=round(build_seconds, 6),
        search_seconds=round(search_seconds, 6),
        top_k=top_k,
        top_score=round(top_hit.score, 6) if top_hit is not None else None,
        top_percentile=round(top_hit.percentile, 6) if top_hit is not None else None,
        top_datetime_utc=top_row.datetime_utc.isoformat() if top_row is not None else None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Astro Global vector index build/search."
    )
    parser.add_argument("--provider", default="synthetic", choices=tuple(PROVIDER_LABELS))
    parser.add_argument(
        "--ephemeris-path",
        type=Path,
        default=None,
        help="Optional Swiss Ephemeris data path; used only with --provider swiss.",
    )
    parser.add_argument("--start", default="1900-01-01", help="UTC start datetime/date.")
    parser.add_argument("--end", default=datetime.now(UTC).date().isoformat(), help="UTC end.")
    parser.add_argument(
        "--query-date",
        default=None,
        help="UTC query datetime/date; defaults to --end.",
    )
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args()

    if args.ephemeris_path is not None and args.provider != "swiss":
        raise SystemExit("--ephemeris-path is only supported with --provider swiss.")

    start = parse_utc(args.start)
    end = parse_utc(args.end)
    query = parse_utc(args.query_date or args.end)
    report = benchmark_index(
        provider_name=args.provider,
        start_utc=start,
        end_utc=end,
        query_utc=query,
        step_days=args.step_days,
        top_k=args.top_k,
        ephemeris_path=args.ephemeris_path,
    )
    payload = json.dumps(asdict(report), indent=2, sort_keys=True)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
