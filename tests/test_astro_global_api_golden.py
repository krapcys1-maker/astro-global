from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.update_resonance_api_golden import DEFAULT_REQUEST
from scripts.update_resonance_compare_golden import DEFAULT_COMPARE_REQUEST
from services.api.app import create_app
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb

AUTH_HEADERS = {"x-astro-global-session": "test-token"}
SEARCH_GOLDEN_PATH = (
    Path(__file__).parent / "golden" / "resonance_search" / "synthetic_2026-05-22T12Z.json"
)
COMPARE_GOLDEN_PATH = (
    Path(__file__).parent
    / "golden"
    / "resonance_compare"
    / "synthetic_2026-05-22T12Z_vs_2020-03-11T00Z.json"
)
COMPARE_PRESETS_GOLDEN_PATH = (
    Path(__file__).parent / "golden" / "resonance_compare" / "presets_swiss_1500_now.json"
)
ARTICLE_SEEDS_GOLDEN_PATH = (
    Path(__file__).parent / "golden" / "articles" / "seeds_swiss_1500_now.json"
)


def test_resonance_search_full_response_matches_golden(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    client = TestClient(create_app(event_db_path=db_path, session_token="test-token"))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json=DEFAULT_REQUEST,
    )

    assert response.status_code == 200
    expected = json.loads(SEARCH_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert response.json() == expected


def test_resonance_compare_full_response_matches_golden(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    client = TestClient(create_app(event_db_path=db_path, session_token="test-token"))

    response = client.post(
        "/resonance/compare",
        headers=AUTH_HEADERS,
        json=DEFAULT_COMPARE_REQUEST,
    )

    assert response.status_code == 200
    expected = json.loads(COMPARE_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert response.json() == expected


def test_resonance_compare_presets_full_response_matches_golden() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/resonance/compare/presets", headers=AUTH_HEADERS)

    assert response.status_code == 200
    expected = json.loads(COMPARE_PRESETS_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert response.json() == expected


def test_article_seeds_full_response_matches_golden() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/articles/seeds", headers=AUTH_HEADERS)

    assert response.status_code == 200
    expected = json.loads(ARTICLE_SEEDS_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert response.json() == expected
