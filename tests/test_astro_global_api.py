from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb

AUTH_HEADERS = {"x-astro-global-session": "test-token"}


def test_health_endpoint() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "astro-global-core"}


def test_data_status_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    missing = client.get("/data/status")
    invalid = client.get("/data/status", headers={"x-astro-global-session": "wrong"})

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_data_status_reports_runtime_capabilities() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/data/status", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "astro-global-core"
    assert payload["profiles"] == ["global_slow_v1"]
    assert payload["providers"]["default_provider"] == "synthetic"
    assert payload["providers"]["synthetic_available"] is True
    assert payload["data_store"]["curated_events_count"] >= 25
    assert payload["security"]["auth_required"] is True
    assert payload["security"]["token_header"] == "x-astro-global-session"
    assert "http://127.0.0.1:5173" in payload["security"]["cors_allowed_origins"]


def test_resonance_search_endpoint_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/search",
        json={"date_utc": "2026-05-22T12:00:00Z"},
    )

    assert response.status_code == 401


def test_sky_at_date_returns_planetary_state() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/sky/at-date",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-22T12:00:00Z"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "synthetic"
    assert payload["ephemeris_version"] == "synthetic-dev"
    assert payload["datetime_utc"] == "2026-05-22T12:00:00+00:00"
    assert len(payload["positions"]) == 10
    assert payload["positions"][0]["body"] == "Sun"
    assert "retrograde" in payload["positions"][0]


def test_sky_current_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/sky/current")

    assert response.status_code == 401


def test_sky_at_date_reports_missing_swiss_provider() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/sky/at-date",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-22T12:00:00Z", "provider": "swiss"},
    )

    if importlib.util.find_spec("swisseph") is None:
        assert response.status_code == 503
        assert "Swiss Ephemeris support requires" in response.json()["detail"]
    else:
        assert response.status_code == 200
        assert response.json()["provider"] == "swiss"


def test_sky_at_date_rejects_unknown_provider() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/sky/at-date",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-22T12:00:00Z", "provider": "unknown"},
    )

    assert response.status_code == 400


def test_resonance_search_endpoint_returns_clustered_episodes() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-05-22T12:00:00Z",
            "lookback_years": 2,
            "lookahead_years": 1,
            "top_k": 20,
            "max_episodes": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_id"] == "global_slow_v1"
    assert payload["provider"] == "synthetic-dev"
    assert payload["index_rows"] > 100
    assert 1 <= len(payload["episodes"]) <= 5
    assert payload["episodes"][0]["best_score"] >= payload["episodes"][-1]["best_score"]
    assert payload["deterministic_summary"]["language"] == "pl"
    assert "nie prognoza" in payload["deterministic_summary"]["summary"]


def test_resonance_search_endpoint_rejects_unknown_profile() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-22T12:00:00Z", "profile_id": "unknown"},
    )

    assert response.status_code == 400


def test_resonance_search_endpoint_returns_matched_events(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    client = TestClient(create_app(event_db_path=db_path, session_token="test-token"))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-05-22T12:00:00Z",
            "lookback_years": 1,
            "lookahead_years": 0,
            "top_k": 10,
            "max_episodes": 3,
            "events_per_episode": 4,
            "event_window_years": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["episodes"]
    assert payload["episodes"][0]["matched_events"]
    assert payload["episodes"][0]["matched_events"][0]["event_id"]
    assert payload["episodes"][0]["matched_events"][0]["sources"]
    assert (
        payload["episodes"][0]["matched_events"][0]["sources"][0]["source_quality"]
        == "wikidata_seed"
    )
    assert payload["episodes"][0]["event_coverage"]["events_found"] >= 1
    assert payload["episodes"][0]["narrative_confidence"]["source_quality_score"] > 0
    assert payload["episodes"][0]["narrative_confidence"]["narrative_confidence"] > 0
    assert (
        payload["episodes"][0]["matched_events"][0]["event_id"]
        in payload["deterministic_summary"]["referenced_event_ids"]
    )
