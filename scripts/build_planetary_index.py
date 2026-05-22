from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.resonance.index_builder import build_weekly_index
from services.resonance.index_store import save_built_index
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID, GLOBAL_SLOW_VECTOR_VERSION

DEFAULT_OUTPUT = ROOT / "data" / "vectors" / "proof_synthetic_global_slow_v1.npz"


def parse_utc(raw: str) -> datetime:
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a persistent Astro Global vector index.")
    parser.add_argument("--provider", default="synthetic", choices=("synthetic",))
    parser.add_argument("--profile", default=GLOBAL_SLOW_PROFILE_ID)
    parser.add_argument("--start", required=True, help="UTC start datetime/date, e.g. 1900-01-01")
    parser.add_argument("--end", required=True, help="UTC end datetime/date, e.g. 2026-05-22")
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.profile != GLOBAL_SLOW_PROFILE_ID:
        raise SystemExit("Only global_slow_v1 is available.")
    if args.step_days < 1:
        raise SystemExit("--step-days must be >= 1.")

    start = parse_utc(args.start)
    end = parse_utc(args.end)
    if end < start:
        raise SystemExit("--end must be >= --start.")

    provider = SyntheticEphemerisProvider()
    built = build_weekly_index(provider, start, end, step_days=args.step_days)
    save_built_index(
        built,
        args.output,
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        provider="synthetic-dev",
        step_days=args.step_days,
    )
    print(
        "\n".join(
            (
                f"Wrote {args.output}",
                f"rows={len(built.rows)}",
                f"dimensions={built.matrix.shape[1] if built.matrix.size else 0}",
                f"start={start.isoformat()}",
                f"end={end.isoformat()}",
                "provider=synthetic-dev",
            )
        )
    )


if __name__ == "__main__":
    main()
