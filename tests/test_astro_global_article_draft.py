from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_article_draft import (
    _live_preflight_result,
    _prompt_preview_result,
    _validate_draft_result,
)
from services.api.schemas import ArticleSeedResponse, ResonanceCompareResponse
from services.narrative.article_draft import (
    ARTICLE_DRAFT_CONTENT_POLICY,
    ARTICLE_DRAFT_EDITORIAL_STATUS,
    build_article_draft_fact_pack,
    build_mock_article_draft,
    validate_article_draft,
)
from services.narrative.article_llm import (
    ArticleDraftLiveConfig,
    ArticleDraftLLMError,
    generate_live_article_draft,
    load_article_draft_live_config_from_env,
    parse_article_draft_output,
)

FIXTURES = Path(__file__).parent / "golden"


def _fixture_seed(seed_id: str = "article_modern_crisis_2019_2022") -> ArticleSeedResponse:
    payload = json.loads((FIXTURES / "articles" / "seeds_swiss_1500_now.json").read_text())
    seeds = {seed["seed_id"]: seed for seed in payload["seeds"]}
    return ArticleSeedResponse.model_validate(seeds[seed_id])


def _fixture_compare() -> ResonanceCompareResponse:
    payload = json.loads(
        (
            FIXTURES
            / "resonance_compare"
            / "synthetic_2026-05-22T12Z_vs_2020-03-11T00Z.json"
        ).read_text()
    )
    return ResonanceCompareResponse.model_validate(payload)


def test_article_draft_fact_pack_uses_only_backend_compare_facts() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )

    assert fact_pack.content_policy == "backend_fact_pack_no_generated_text"
    assert fact_pack.output_policy == ARTICLE_DRAFT_CONTENT_POLICY
    assert fact_pack.editorial_status_required == ARTICLE_DRAFT_EDITORIAL_STATUS
    assert "evt_covid_19_pandemic" in fact_pack.allowed_event_ids
    assert "src_evt_covid_19_pandemic_cdc" in fact_pack.allowed_source_ids
    assert "Neptune-Pluto:square" in fact_pack.shared_primary_cycles
    assert any("Use only event_ids" in rule for rule in fact_pack.writing_constraints)
    assert any("not generated articles" in warning for warning in fact_pack.warnings)


def test_mock_article_draft_validates_against_fact_pack() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack)
    result = validate_article_draft(fact_pack=fact_pack, draft=draft)

    assert result.ok, result.errors
    assert draft.editorial_status == ARTICLE_DRAFT_EDITORIAL_STATUS
    assert set(draft.used_event_ids) <= set(fact_pack.allowed_event_ids)
    assert set(draft.used_source_ids) <= set(fact_pack.allowed_source_ids)


def test_article_draft_validator_rejects_hallucinated_event_ids() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack).model_copy(
        update={"used_event_ids": ("evt_covid_19_pandemic", "evt_hallucinated")}
    )
    result = validate_article_draft(fact_pack=fact_pack, draft=draft)

    assert not result.ok
    assert any("evt_hallucinated" in error for error in result.errors)


def test_article_draft_validator_rejects_predictive_language() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack)
    bad_section = draft.sections[0].model_copy(
        update={"paragraphs": ("Pewne jest, ze to sie wydarzy.",)}
    )
    bad_draft = draft.model_copy(update={"sections": (bad_section, *draft.sections[1:])})
    result = validate_article_draft(fact_pack=fact_pack, draft=bad_draft)

    assert not result.ok
    assert any("forbidden predictive phrase" in error for error in result.errors)


def test_article_llm_parser_accepts_fenced_json() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack)

    parsed = parse_article_draft_output(f"```json\n{draft.model_dump_json()}\n```")

    assert parsed.seed_id == draft.seed_id
    assert parsed.editorial_status == ARTICLE_DRAFT_EDITORIAL_STATUS


def test_live_article_draft_uses_openai_compatible_transport() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    expected_draft = build_mock_article_draft(fact_pack)

    def fake_transport(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        assert isinstance(payload, dict)
        assert payload["model"] == "local-test-model"
        assert payload["response_format"] == {"type": "json_object"}
        assert kwargs["api_key"] == "test-key"
        return {
            "choices": [
                {
                    "message": {
                        "content": expected_draft.model_dump_json(),
                    }
                }
            ]
        }

    draft, raw_content = generate_live_article_draft(
        fact_pack=fact_pack,
        config=ArticleDraftLiveConfig(
            base_url="https://llm.example.test/chat/completions",
            api_key="test-key",
            model="local-test-model",
        ),
        transport=fake_transport,
    )
    result = validate_article_draft(fact_pack=fact_pack, draft=draft)

    assert result.ok, result.errors
    assert raw_content == expected_draft.model_dump_json()


def test_live_article_draft_config_requires_explicit_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "ASTRO_GLOBAL_LLM_BASE_URL",
        "ASTRO_GLOBAL_LLM_API_KEY",
        "ASTRO_GLOBAL_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    try:
        load_article_draft_live_config_from_env()
    except ArticleDraftLLMError as exc:
        assert "ASTRO_GLOBAL_LLM_BASE_URL" in str(exc)
    else:
        raise AssertionError("Expected missing env vars to fail closed.")


def test_live_preflight_reports_missing_env_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "ASTRO_GLOBAL_LLM_BASE_URL",
        "ASTRO_GLOBAL_LLM_API_KEY",
        "ASTRO_GLOBAL_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )

    result = _live_preflight_result(seed_id=fact_pack.seed_id, fact_pack=fact_pack)

    assert result["mode"] == "live-preflight"
    assert result["live_ready"] is False
    assert "ASTRO_GLOBAL_LLM_BASE_URL" in result["error"]
    assert result["fact_pack_summary"]["allowed_event_ids"] > 0


def test_prompt_preview_builds_messages_without_provider_call() -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )

    result = _prompt_preview_result(seed_id=fact_pack.seed_id, fact_pack=fact_pack)

    assert result["mode"] == "prompt-preview"
    assert result["provider"] == {"mode": "none", "request_sent": False}
    assert result["prompt_summary"]["message_count"] == 2
    assert result["prompt_summary"]["allowed_event_ids"] > 0
    assert "fact_pack" in result["messages"][1]["content"]


def test_validate_draft_accepts_manual_draft_wrapper(tmp_path: Path) -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack)
    draft_input = tmp_path / "draft_wrapper.json"
    draft_input.write_text(
        json.dumps({"draft": draft.model_dump(mode="json")}),
        encoding="utf-8",
    )

    result = _validate_draft_result(
        seed_id=fact_pack.seed_id,
        fact_pack=fact_pack,
        draft_input=draft_input,
    )

    assert result["mode"] == "validate-draft"
    assert result["provider"] == {"mode": "manual", "request_sent": False}
    assert result["validation"]["ok"] is True


def test_validate_draft_reports_manual_hallucination(tmp_path: Path) -> None:
    fact_pack = build_article_draft_fact_pack(
        seed=_fixture_seed(),
        compare=_fixture_compare(),
    )
    draft = build_mock_article_draft(fact_pack).model_copy(
        update={"used_source_ids": ("src_not_allowed",)}
    )
    draft_input = tmp_path / "bad_draft.json"
    draft_input.write_text(draft.model_dump_json(), encoding="utf-8")

    result = _validate_draft_result(
        seed_id=fact_pack.seed_id,
        fact_pack=fact_pack,
        draft_input=draft_input,
    )

    assert result["validation"]["ok"] is False
    assert any("src_not_allowed" in error for error in result["validation"]["errors"])
