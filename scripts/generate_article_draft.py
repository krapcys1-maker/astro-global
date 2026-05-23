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
from services.narrative.article_llm import (
    ArticleDraftLLMError,
    build_article_draft_messages,
    generate_live_article_draft,
    load_article_draft_live_config_from_env,
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


def _build_fact_pack(args: argparse.Namespace) -> tuple[str, Any]:
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
    return seed.seed_id, fact_pack


def _run(args: argparse.Namespace) -> dict[str, Any]:
    seed_id, fact_pack = _build_fact_pack(args)
    if args.mode == "prompt-preview":
        return _prompt_preview_result(seed_id=seed_id, fact_pack=fact_pack)
    if args.mode == "live-preflight":
        return _live_preflight_result(seed_id=seed_id, fact_pack=fact_pack)

    provider = {"mode": "mock"}
    if args.mode == "mock":
        draft = build_mock_article_draft(fact_pack)
        raw_llm_content = None
    else:
        try:
            live_config = load_article_draft_live_config_from_env()
            draft, raw_llm_content = generate_live_article_draft(
                fact_pack=fact_pack,
                config=live_config,
            )
        except ArticleDraftLLMError as exc:
            raise SystemExit(str(exc)) from exc
        provider = {"mode": "live", **live_config.public_summary()}

    validation = validate_article_draft(fact_pack=fact_pack, draft=draft)
    _assert(
        validation.ok,
        f"{args.mode} article draft validation failed: " + "; ".join(validation.errors),
    )
    return {
        "mode": args.mode,
        "seed_id": seed_id,
        "provider": provider,
        "fact_pack": fact_pack.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
        "raw_llm_content": raw_llm_content,
    }


def _prompt_preview_result(*, seed_id: str, fact_pack: Any) -> dict[str, Any]:
    messages = build_article_draft_messages(fact_pack)
    serialized_messages = json.dumps(messages, ensure_ascii=False)
    return {
        "mode": "prompt-preview",
        "seed_id": seed_id,
        "provider": {"mode": "none", "request_sent": False},
        "messages": messages,
        "prompt_summary": {
            "message_count": len(messages),
            "serialized_chars": len(serialized_messages),
            "content_policy": fact_pack.content_policy,
            "output_policy": fact_pack.output_policy,
            "editorial_status_required": fact_pack.editorial_status_required,
            "allowed_event_ids": len(fact_pack.allowed_event_ids),
            "allowed_source_ids": len(fact_pack.allowed_source_ids),
            "episodes": len(fact_pack.episodes),
            "warnings": list(fact_pack.warnings),
        },
    }


def _live_preflight_result(*, seed_id: str, fact_pack: Any) -> dict[str, Any]:
    try:
        live_config = load_article_draft_live_config_from_env()
    except ArticleDraftLLMError as exc:
        return {
            "mode": "live-preflight",
            "seed_id": seed_id,
            "live_ready": False,
            "provider": {"mode": "live", "configured": False},
            "error": str(exc),
            "fact_pack_summary": _fact_pack_summary(fact_pack),
        }
    return {
        "mode": "live-preflight",
        "seed_id": seed_id,
        "live_ready": True,
        "provider": {
            "mode": "live",
            "configured": True,
            **live_config.public_summary(),
        },
        "fact_pack_summary": _fact_pack_summary(fact_pack),
    }


def _fact_pack_summary(fact_pack: Any) -> dict[str, Any]:
    return {
        "content_policy": fact_pack.content_policy,
        "output_policy": fact_pack.output_policy,
        "editorial_status_required": fact_pack.editorial_status_required,
        "allowed_event_ids": len(fact_pack.allowed_event_ids),
        "allowed_source_ids": len(fact_pack.allowed_source_ids),
        "episodes": len(fact_pack.episodes),
        "warnings": list(fact_pack.warnings),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and validate a local article draft package from backend facts."
    )
    parser.add_argument("--seed-id", default=DEFAULT_SEED_ID)
    parser.add_argument(
        "--mode",
        choices=("mock", "prompt-preview", "live-preflight", "live"),
        default="mock",
    )
    parser.add_argument("--vector-index-root", default=str(ROOT / "data" / "vectors"))
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE)
    parser.add_argument(
        "--output",
        default=None,
    )
    args = parser.parse_args()
    result = _run(args)
    output_path = Path(args.output or _default_output_path(args.mode))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            _stdout_summary(result=result, output_path=output_path),
            ensure_ascii=False,
            indent=2,
        )
    )


def _stdout_summary(*, result: dict[str, Any], output_path: Path) -> dict[str, Any]:
    summary = {
        "seed_id": result["seed_id"],
        "mode": result["mode"],
        "provider": result["provider"],
        "output": str(output_path),
    }
    if "validation" in result:
        summary["validation_ok"] = result["validation"]["ok"]
    if "live_ready" in result:
        summary["live_ready"] = result["live_ready"]
    if "error" in result:
        summary["error"] = result["error"]
    if "prompt_summary" in result:
        summary["prompt_summary"] = result["prompt_summary"]
    return summary


def _default_output_path(mode: str) -> str:
    return str(ROOT / "work" / "reports" / f"article_draft_{mode}.json")


if __name__ == "__main__":
    main()
