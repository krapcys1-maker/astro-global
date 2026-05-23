from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api import product_catalog

REQUIRED_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"


def test_compare_presets_are_anchored_to_curated_event_years() -> None:
    response = product_catalog.resonance_compare_presets_response(
        required_index_file=REQUIRED_INDEX_FILE,
    )

    presets = {preset.preset_id: preset for preset in response.presets}
    revolutionary = presets["revolutionary_wave_1789_1848"]

    assert response.provider == "swiss"
    assert response.index_file == REQUIRED_INDEX_FILE
    assert response.date_policy == "curated_start_year_to_utc_year_start"
    assert revolutionary.left_event.event_id == "evt_french_revolution"
    assert revolutionary.left_event.date_utc == "1789-01-01T00:00:00Z"
    assert revolutionary.left_event.date_precision == "year_start_anchor"
    assert revolutionary.compare_request.provider == "swiss"
    assert revolutionary.compare_request.index_file == REQUIRED_INDEX_FILE
    assert revolutionary.compare_request.left_date_utc.year == (
        revolutionary.left_event.start_astro_year
    )
    assert any("not a prediction" in warning for warning in revolutionary.warnings)


def test_article_seeds_only_reference_backend_compare_presets() -> None:
    response = product_catalog.article_seeds_response(
        required_index_file=REQUIRED_INDEX_FILE,
    )

    seeds = {seed.seed_id: seed for seed in response.seeds}
    revolutionary = seeds["article_revolutionary_wave_1789_1848"]

    assert response.content_policy == "seed_only_no_generated_article_text"
    assert revolutionary.editorial_status == "seed_only_not_article"
    assert revolutionary.compare_preset_id == "revolutionary_wave_1789_1848"
    assert revolutionary.source_event_ids == (
        "evt_french_revolution",
        "evt_revolutions_1848",
    )
    assert revolutionary.compare_request.index_file == REQUIRED_INDEX_FILE
    assert "POST /resonance/compare" in revolutionary.allowed_next_api_calls
    assert any("not generated articles" in warning for warning in revolutionary.warnings)


def test_compare_presets_fail_closed_when_curated_event_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_catalog,
        "COMPARE_PRESET_DEFINITIONS",
        (
            {
                "preset_id": "broken_preset",
                "label": "Broken preset",
                "left_event_id": "evt_missing",
                "right_event_id": "evt_french_revolution",
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        product_catalog.resonance_compare_presets_response(
            required_index_file=REQUIRED_INDEX_FILE,
        )

    assert exc_info.value.status_code == 500
    assert "evt_missing" in str(exc_info.value.detail)


def test_article_seeds_fail_closed_when_compare_preset_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_catalog,
        "ARTICLE_SEED_DEFINITIONS",
        (
            {
                "seed_id": "broken_seed",
                "title": "Broken seed",
                "summary": "This seed points to a missing compare preset.",
                "compare_preset_id": "missing_preset",
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        product_catalog.article_seeds_response(required_index_file=REQUIRED_INDEX_FILE)

    assert exc_info.value.status_code == 500
    assert "missing_preset" in str(exc_info.value.detail)
