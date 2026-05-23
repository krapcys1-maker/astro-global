from __future__ import annotations

import json
from pathlib import Path

from services.api.schemas import ArticleSeedResponse, ResonanceCompareResponse
from services.narrative.article_draft import (
    ARTICLE_DRAFT_CONTENT_POLICY,
    ARTICLE_DRAFT_EDITORIAL_STATUS,
    build_article_draft_fact_pack,
    build_mock_article_draft,
    validate_article_draft,
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
