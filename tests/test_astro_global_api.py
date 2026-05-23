from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.resonance.index_builder import build_weekly_index
from services.resonance.index_store import save_built_index

AUTH_HEADERS = {"x-astro-global-session": "test-token"}


def datetime_from_iso(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


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
    assert payload["data_store"]["curated_event_sources_count"] >= payload["data_store"][
        "curated_events_count"
    ]
    assert payload["data_store"]["event_kind_counts"]["war"] >= 1
    assert payload["data_store"]["source_quality_counts"]["encyclopedic"] >= 1
    assert payload["data_store"]["source_precision_counts"]["direct"] >= 1
    assert payload["data_store"]["source_precision_counts"].get("contextual", 0) == 0
    assert payload["data_store"]["source_precision_counts"].get("broad_context", 0) == 0
    assert payload["data_store"]["ongoing_events_count"] >= 6
    assert "evt_russian_invasion_ukraine" in payload["data_store"]["ongoing_event_ids"]
    assert payload["data_store"]["events_without_curated_sources"] == []
    assert payload["data_store"]["weak_precision_events_without_direct_backup"] == []
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


def test_events_window_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get(
        "/events/window",
        params={"start_astro_year": 2020, "end_astro_year": 2026},
    )

    assert response.status_code == 401


def test_events_window_returns_events_sources_and_coverage(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    client = TestClient(create_app(event_db_path=db_path, session_token="test-token"))

    response = client.get(
        "/events/window",
        headers=AUTH_HEADERS,
        params={"start_astro_year": 2020, "end_astro_year": 2026, "limit": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["start_astro_year"] == 2020
    assert payload["end_astro_year"] == 2026
    assert payload["limit"] == 6
    assert 1 <= len(payload["events"]) <= 6
    assert payload["event_coverage"]["events_found"] == len(payload["events"])
    assert payload["event_coverage"]["event_kinds"]
    assert payload["event_coverage"]["ongoing_events_count"] >= 1
    assert any(event["event_id"] == "evt_covid_19_pandemic" for event in payload["events"])
    assert all(event["sources"] for event in payload["events"])
    covid = next(
        event for event in payload["events"] if event["event_id"] == "evt_covid_19_pandemic"
    )
    assert covid["is_ongoing"] is True
    assert covid["end_year_policy"] == "build_year"
    assert {source["source_quality"] for source in covid["sources"]} >= {
        "wikidata_seed",
        "institutional",
    }
    assert {source["source_precision"] for source in covid["sources"]} >= {
        "structured_reference",
        "direct",
    }


def test_events_window_rejects_invalid_year_range() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get(
        "/events/window",
        headers=AUTH_HEADERS,
        params={"start_astro_year": 2026, "end_astro_year": 2020},
    )

    assert response.status_code == 400


def test_events_window_can_return_empty_result() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get(
        "/events/window",
        headers=AUTH_HEADERS,
        params={"start_astro_year": 1490, "end_astro_year": 1499},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"] == []
    assert payload["event_coverage"]["events_found"] == 0
    assert payload["event_coverage"]["warning"] == "No historical events found for this period."


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
    assert payload["index_source"] == "in_memory"
    assert payload["index_artifact"] is None
    assert payload["index_rows"] > 100
    assert 1 <= len(payload["episodes"]) <= 5
    assert payload["episodes"][0]["best_score"] >= payload["episodes"][-1]["best_score"]
    assert payload["episodes"][0]["score_breakdown"]["label"] in {
        "strong",
        "moderate",
        "weak",
        "rare_configuration",
        "insufficient_comparable_history",
    }
    assert (
        payload["episodes"][0]["score_breakdown"]["planetary_resonance_score"]
        >= payload["episodes"][0]["score_breakdown"]["structural_similarity"] * 0.60
    )
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


def test_resonance_search_can_use_persistent_index(tmp_path: Path) -> None:
    query_dt = "2026-05-22T12:00:00Z"
    start_utc = "2025-05-22T12:00:00+00:00"
    end_utc = "2026-05-22T12:00:00+00:00"
    built = build_weekly_index(
        SyntheticEphemerisProvider(),
        datetime_from_iso(start_utc),
        datetime_from_iso(end_utc),
        step_days=7,
    )
    save_built_index(
        built,
        tmp_path / "proof_index.npz",
        profile_id="global_slow_v1",
        vector_version="global_slow_v1.0",
        provider="synthetic-dev",
        step_days=7,
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": query_dt,
            "lookback_years": 1,
            "lookahead_years": 0,
            "top_k": 10,
            "max_episodes": 3,
            "index_file": "proof_index.npz",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_source"] == "persistent_npz"
    assert payload["index_artifact"] == "proof_index.npz"
    assert payload["index_rows"] == len(built.rows)


def test_resonance_search_rejects_index_path_traversal() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-05-22T12:00:00Z",
            "index_file": "../outside.npz",
        },
    )

    assert response.status_code == 400


def test_resonance_search_rejects_mismatched_persistent_index(tmp_path: Path) -> None:
    built = build_weekly_index(
        SyntheticEphemerisProvider(),
        datetime_from_iso("2026-01-01T00:00:00+00:00"),
        datetime_from_iso("2026-02-01T00:00:00+00:00"),
        step_days=7,
    )
    save_built_index(
        built,
        tmp_path / "mismatch.npz",
        profile_id="global_slow_v1",
        vector_version="global_slow_v1.0",
        provider="synthetic-dev",
        step_days=7,
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-05-22T12:00:00Z",
            "lookback_years": 1,
            "lookahead_years": 0,
            "index_file": "mismatch.npz",
        },
    )

    assert response.status_code == 400
    assert "Index start does not match request" in response.json()["detail"]


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
    assert "omitted_point_events" in payload["episodes"][0]
    assert payload["episodes"][0]["matched_events"][0]["event_id"]
    assert payload["episodes"][0]["matched_events"][0]["sources"]
    first_event_sources = payload["episodes"][0]["matched_events"][0]["sources"]
    first_event_source_qualities = {source["source_quality"] for source in first_event_sources}
    all_event_source_qualities = {
        source["source_quality"]
        for event in payload["episodes"][0]["matched_events"]
        for source in event["sources"]
    }
    assert "wikidata_seed" in first_event_source_qualities
    assert first_event_source_qualities - {"wikidata_seed"}
    assert all_event_source_qualities & {"encyclopedic", "institutional", "primary"}
    assert payload["episodes"][0]["event_coverage"]["events_found"] >= 1
    assert payload["episodes"][0]["score_breakdown"]["cycle_power_score"] > 0
    assert payload["episodes"][0]["score_breakdown"]["label"] == "strong"
    assert payload["episodes"][0]["narrative_confidence"]["source_quality_score"] > 0
    assert payload["episodes"][0]["narrative_confidence"]["narrative_confidence"] > 0
    assert (
        payload["episodes"][0]["matched_events"][0]["event_id"]
        in payload["deterministic_summary"]["referenced_event_ids"]
    )
