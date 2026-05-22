from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.update_resonance_api_golden import DEFAULT_REQUEST
from services.api.app import create_app
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb

AUTH_HEADERS = {"x-astro-global-session": "test-token"}
GOLDEN_PATH = (
    Path(__file__).parent / "golden" / "resonance_search" / "synthetic_2026-05-22T12Z.json"
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
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert response.json() == expected
