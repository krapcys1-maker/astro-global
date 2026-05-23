from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app
from services.api.schemas import ArticleSeedResponse
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.narrative.article_draft import (
    build_article_draft_fact_pack,
    build_mock_article_draft,
    validate_article_draft,
)

DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"
DEFAULT_SEED_ID = "article_revolutionary_wave_1789_1848"
SESSION_TOKEN = "article-draft-local-token"
AUTH_HEADERS = {"x-astro-global-session": SESSION_TOKEN}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _json_response(response: Any, *, label: str) -> dict[str, Any]:
    _assert(response.status_code == 200, f"{label} failed: {response.text}")
    return dict(response.json())


def _select_seed(payload: dict[str, Any], seed_id: str) -> ArticleSeedResponse:
    seeds = {
        str(seed["seed_id"]): ArticleSeedResponse.model_validate(seed)
        for seed in payload.get("seeds", [])
    }
    _assert(bool(seeds), "/articles/seeds returned no seeds.")
    _assert(seed_id in seeds, f"Unknown seed_id {seed_id!r}; available: {', '.join(seeds)}")
    return seeds[seed_id]


def _run(args: argparse.Namespace) -> dict[str, Any]:
    index_path = Path(args.vector_index_root) / args.index_file
    _assert(
        index_path.exists(),
        (
            f"Missing Swiss index: {index_path}. Build it with "
            "scripts/build_planetary_index.py before generating article draft input."
        ),
    )
    with tempfile.TemporaryDirectory(prefix="astro-global-article-draft-") as tmp:
        db_path = Path(tmp) / "astro_global.duckdb"
        write_events_to_duckdb(db_path, load_curated_events())
        client = TestClient(
            create_app(
                event_db_path=db_path,
                vector_index_root=args.vector_index_root,
                required_index_file=args.index_file,
                session_token=SESSION_TOKEN,
            )
        )
        seeds_payload = _json_response(
            client.get("/articles/seeds", headers=AUTH_HEADERS),
            label="/articles/seeds",
        )
        seed = _select_seed(seeds_payload, args.seed_id)
        compare_payload = _json_response(
            client.post(
                "/resonance/compare",
                headers=AUTH_HEADERS,
                json=seed.compare_request.model_dump(mode="json"),
            ),
            label="/resonance/compare",
        )

    from services.api.schemas import ResonanceCompareResponse

    compare = ResonanceCompareResponse.model_validate(compare_payload)
    fact_pack = build_article_draft_fact_pack(seed=seed, compare=compare)
    draft = build_mock_article_draft(fact_pack)
    validation = validate_article_draft(fact_pack=fact_pack, draft=draft)
    _assert(validation.ok, "Mock article draft validation failed: " + "; ".join(validation.errors))
    return {
        "mode": "mock",
        "seed_id": seed.seed_id,
        "fact_pack": fact_pack.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and validate a local article draft package from backend facts."
    )
    parser.add_argument("--seed-id", default=DEFAULT_SEED_ID)
    parser.add_argument("--mode", choices=("mock",), default="mock")
    parser.add_argument("--vector-index-root", default=str(ROOT / "data" / "vectors"))
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE)
    parser.add_argument(
        "--output",
        default=str(ROOT / "work" / "reports" / "article_draft_mock.json"),
    )
    args = parser.parse_args()
    result = _run(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "seed_id": result["seed_id"],
                "mode": result["mode"],
                "validation_ok": result["validation"]["ok"],
                "output": str(output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
