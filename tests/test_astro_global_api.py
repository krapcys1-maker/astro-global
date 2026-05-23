from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from services.api.app import _split_context_events, create_app
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.resonance.index_builder import BuiltIndex, IndexRow, build_weekly_index
from services.resonance.index_store import save_built_index
from services.resonance.vectorizer import GLOBAL_SLOW_VECTOR_VERSION

AUTH_HEADERS = {"x-astro-global-session": "test-token"}


def datetime_from_iso(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def save_sparse_synthetic_index(
    path: Path,
    datetimes: tuple[datetime, ...],
) -> None:
    rows = tuple(
        IndexRow(row_index=index, datetime_utc=dt, julian_day_ut=float(index + 1))
        for index, dt in enumerate(datetimes)
    )
    matrix = np.ones((len(rows), 104), dtype=np.float64)
    save_built_index(
        BuiltIndex(matrix=matrix, rows=rows),
        path,
        profile_id="global_slow_v1",
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        provider="synthetic-dev",
        step_days=7,
    )


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
    assert payload["security"]["runtime_environment"] == "development"
    assert payload["security"]["auth_required"] is True
    assert payload["security"]["token_header"] == "x-astro-global-session"
    assert "http://127.0.0.1:5173" in payload["security"]["cors_allowed_origins"]
    assert payload["security"]["rate_limit_enabled"] is False
    assert payload["security"]["rate_limit_per_minute"] == 60
    assert payload["security"]["max_request_bytes"] == 65536


def test_today_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/today")

    assert response.status_code == 401


def test_today_returns_daily_backend_snapshot() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/today", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.headers["x-astro-global-snapshot-date"] == response.json()[
        "snapshot_date_utc"
    ]
    assert "max-age=300" in response.headers["cache-control"]
    payload = response.json()
    assert payload["service"] == "astro-global-core"
    assert payload["profile_id"] == "global_slow_v1"
    assert payload["provider"] == "swiss"
    assert payload["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert payload["reliable_history_start"] == 1500
    assert payload["reliable_history_end"] == 2026
    assert payload["history_window_label"] == "reliable_modern"
    request = payload["recommended_search_request"]
    assert request["profile_id"] == "global_slow_v1"
    assert request["provider"] == "swiss"
    assert request["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert request["lookback_years"] == 120
    assert any("not a prediction" in warning for warning in payload["warnings"])


def test_production_api_requires_explicit_session_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.delenv("ASTRO_GLOBAL_SESSION_TOKEN", raising=False)
    monkeypatch.setenv("ASTRO_GLOBAL_CORS_ORIGINS", "https://astro.example")

    with pytest.raises(RuntimeError, match="ASTRO_GLOBAL_SESSION_TOKEN is required"):
        create_app()


def test_production_api_requires_explicit_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.setenv("ASTRO_GLOBAL_SESSION_TOKEN", "prod-token")
    monkeypatch.delenv("ASTRO_GLOBAL_CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError, match="ASTRO_GLOBAL_CORS_ORIGINS is required"):
        create_app()


def test_production_api_uses_env_token_and_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.setenv("ASTRO_GLOBAL_SESSION_TOKEN", "prod-token")
    monkeypatch.setenv(
        "ASTRO_GLOBAL_CORS_ORIGINS",
        "https://astro.example, https://www.astro.example",
    )

    client = TestClient(create_app())
    missing = client.get("/data/status")
    ready = client.get("/data/status", headers={"x-astro-global-session": "prod-token"})

    assert missing.status_code == 401
    assert ready.status_code == 200
    security = ready.json()["security"]
    assert security["runtime_environment"] == "production"
    assert security["cors_allowed_origins"] == [
        "https://astro.example",
        "https://www.astro.example",
    ]
    assert security["rate_limit_enabled"] is True
    assert security["rate_limit_per_minute"] == 60
    assert security["max_request_bytes"] == 65536


def test_api_rate_limit_blocks_after_configured_limit() -> None:
    client = TestClient(
        create_app(
            session_token="test-token",
            rate_limit_enabled=True,
            rate_limit_per_minute=2,
        )
    )

    first = client.get("/data/status", headers=AUTH_HEADERS)
    second = client.get("/data/status", headers=AUTH_HEADERS)
    limited = client.get("/data/status", headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Astro Global API rate limit exceeded."
    assert int(limited.headers["Retry-After"]) >= 1


def test_api_rate_limit_uses_client_forwarded_for() -> None:
    client = TestClient(
        create_app(
            session_token="test-token",
            rate_limit_enabled=True,
            rate_limit_per_minute=1,
        )
    )
    first_client_headers = AUTH_HEADERS | {"x-forwarded-for": "198.51.100.10"}
    second_client_headers = AUTH_HEADERS | {"x-forwarded-for": "198.51.100.11"}

    first = client.get("/data/status", headers=first_client_headers)
    limited = client.get("/data/status", headers=first_client_headers)
    other_client = client.get("/data/status", headers=second_client_headers)

    assert first.status_code == 200
    assert limited.status_code == 429
    assert other_client.status_code == 200


def test_api_rate_limit_skips_health_and_readiness(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            event_db_path=tmp_path / "missing.duckdb",
            vector_index_root=tmp_path,
            session_token="test-token",
            rate_limit_enabled=True,
            rate_limit_per_minute=1,
        )
    )

    health_first = client.get("/health")
    health_second = client.get("/health")
    readiness_first = client.get("/readiness", headers=AUTH_HEADERS)
    readiness_second = client.get("/readiness", headers=AUTH_HEADERS)

    assert health_first.status_code == 200
    assert health_second.status_code == 200
    assert readiness_first.status_code == 503
    assert readiness_second.status_code == 503


def test_api_rate_limit_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.setenv("ASTRO_GLOBAL_SESSION_TOKEN", "prod-token")
    monkeypatch.setenv("ASTRO_GLOBAL_CORS_ORIGINS", "https://astro.example")
    monkeypatch.setenv("ASTRO_GLOBAL_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE", "7")

    client = TestClient(create_app())
    response = client.get("/data/status", headers={"x-astro-global-session": "prod-token"})

    assert response.status_code == 200
    security = response.json()["security"]
    assert security["rate_limit_enabled"] is False
    assert security["rate_limit_per_minute"] == 7


def test_api_rejects_request_body_over_configured_limit() -> None:
    client = TestClient(
        create_app(
            session_token="test-token",
            max_request_bytes=24,
        )
    )

    response = client.post(
        "/sky/at-date",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-23T00:00:00Z", "provider": "synthetic"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Astro Global API request body too large.",
        "max_request_bytes": 24,
    }


def test_api_accepts_request_body_under_configured_limit() -> None:
    client = TestClient(
        create_app(
            session_token="test-token",
            max_request_bytes=512,
        )
    )

    response = client.post(
        "/sky/at-date",
        headers=AUTH_HEADERS,
        json={"date_utc": "2026-05-23T00:00:00Z", "provider": "synthetic"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "synthetic"


def test_api_request_size_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.setenv("ASTRO_GLOBAL_SESSION_TOKEN", "prod-token")
    monkeypatch.setenv("ASTRO_GLOBAL_CORS_ORIGINS", "https://astro.example")
    monkeypatch.setenv("ASTRO_GLOBAL_MAX_REQUEST_BYTES", "4096")

    client = TestClient(create_app())
    response = client.get("/data/status", headers={"x-astro-global-session": "prod-token"})

    assert response.status_code == 200
    assert response.json()["security"]["max_request_bytes"] == 4096


def test_api_rejects_invalid_request_size_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_MAX_REQUEST_BYTES", "0")

    with pytest.raises(RuntimeError, match="ASTRO_GLOBAL_MAX_REQUEST_BYTES must be >= 1"):
        create_app(session_token="test-token")


def test_production_api_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTRO_GLOBAL_ENV", "production")
    monkeypatch.setenv("ASTRO_GLOBAL_SESSION_TOKEN", "prod-token")
    monkeypatch.setenv("ASTRO_GLOBAL_CORS_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="must not contain wildcard"):
        create_app()


def test_readiness_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/readiness")

    assert response.status_code == 401


def test_readiness_reports_ready_product_path(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    save_sparse_synthetic_index(
        tmp_path / "swiss_1500_now_global_slow_v1.npz",
        (
            datetime(1500, 1, 1, tzinfo=UTC),
            datetime(1789, 7, 14, tzinfo=UTC),
            datetime(2026, 5, 23, tzinfo=UTC),
        ),
    )
    client = TestClient(
        create_app(
            event_db_path=db_path,
            vector_index_root=tmp_path,
            session_token="test-token",
        )
    )

    response = client.get("/readiness", headers=AUTH_HEADERS)

    if importlib.util.find_spec("swisseph") is None:
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
        return
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["required_index_file"] == "swiss_1500_now_global_slow_v1.npz"
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["swiss_ephemeris"]["status"] == "ready"
    assert checks["event_store"]["status"] == "ready"
    assert checks["curated_data"]["status"] == "ready"
    assert checks["reliable_index"]["status"] == "ready"


def test_readiness_reports_missing_duckdb_and_index(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            event_db_path=tmp_path / "missing.duckdb",
            vector_index_root=tmp_path,
            session_token="test-token",
        )
    )

    response = client.get("/readiness", headers=AUTH_HEADERS)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["event_store"]["status"] == "not_ready"
    assert checks["reliable_index"]["status"] == "not_ready"


def test_readiness_rejects_index_that_starts_after_reliable_history(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    save_sparse_synthetic_index(
        tmp_path / "swiss_1900_now_global_slow_v1.npz",
        (
            datetime(1900, 1, 1, tzinfo=UTC),
            datetime(2026, 5, 23, tzinfo=UTC),
        ),
    )
    client = TestClient(
        create_app(
            event_db_path=db_path,
            vector_index_root=tmp_path,
            required_index_file="swiss_1900_now_global_slow_v1.npz",
            session_token="test-token",
        )
    )

    response = client.get("/readiness", headers=AUTH_HEADERS)

    assert response.status_code == 503
    checks = {check["name"]: check for check in response.json()["checks"]}
    assert checks["reliable_index"]["status"] == "not_ready"
    assert "after reliable start" in checks["reliable_index"]["detail"]


def test_resonance_search_endpoint_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/search",
        json={"date_utc": "2026-05-22T12:00:00Z"},
    )

    assert response.status_code == 401


def test_resonance_compare_requires_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/compare",
        json={
            "left_date_utc": "2026-05-22T12:00:00Z",
            "right_date_utc": "1789-07-14T00:00:00Z",
        },
    )

    assert response.status_code == 401


def test_resonance_compare_returns_deterministic_backend_comparison() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/compare",
        headers=AUTH_HEADERS,
        json={
            "left_date_utc": "2026-05-22T12:00:00Z",
            "right_date_utc": "2020-03-11T00:00:00Z",
            "lookback_years": 3,
            "lookahead_years": 0,
            "top_k": 20,
            "max_episodes": 3,
            "events_per_episode": 4,
            "provider": "synthetic",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_id"] == "global_slow_v1"
    assert payload["provider"] == "synthetic-dev"
    assert 0.0 <= payload["query_vector_similarity"] <= 1.0
    assert payload["left"]["query_datetime_utc"] == "2026-05-22T12:00:00+00:00"
    assert payload["right"]["query_datetime_utc"] == "2020-03-11T00:00:00+00:00"
    assert payload["left"]["episodes"]
    assert payload["right"]["episodes"]
    assert "nie prognoza" in payload["deterministic_summary"]
    assert any("not a prediction" in warning for warning in payload["warnings"])


def test_resonance_compare_rejects_index_path_traversal() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.post(
        "/resonance/compare",
        headers=AUTH_HEADERS,
        json={
            "left_date_utc": "2026-05-22T12:00:00Z",
            "right_date_utc": "2020-03-11T00:00:00Z",
            "index_file": "../outside.npz",
        },
    )

    assert response.status_code == 400


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


def test_resonance_search_can_use_broader_persistent_index(tmp_path: Path) -> None:
    built = build_weekly_index(
        SyntheticEphemerisProvider(),
        datetime_from_iso("2024-05-22T12:00:00+00:00"),
        datetime_from_iso("2026-05-22T12:00:00+00:00"),
        step_days=7,
    )
    save_built_index(
        built,
        tmp_path / "broad_index.npz",
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
            "top_k": 10,
            "max_episodes": 3,
            "index_file": "broad_index.npz",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_source"] == "persistent_npz"
    assert payload["index_artifact"] == "broad_index.npz"
    assert 1 <= payload["index_rows"] < len(built.rows)
    assert payload["index_coverage"]["index_coverage_status"] == "full"
    assert payload["index_coverage"]["history_window_label"] == "reliable_modern"
    assert payload["episodes"]


def test_resonance_search_accepts_reliable_1500_index_for_1600_to_now_request(
    tmp_path: Path,
) -> None:
    save_sparse_synthetic_index(
        tmp_path / "swiss_1500_now_global_slow_v1.npz",
        (
            datetime(1500, 1, 1, tzinfo=UTC),
            datetime(1600, 1, 1, tzinfo=UTC),
            datetime(1789, 7, 14, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-01-01T00:00:00Z",
            "lookback_years": 426,
            "lookahead_years": 0,
            "top_k": 4,
            "max_episodes": 4,
            "index_file": "swiss_1500_now_global_slow_v1.npz",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_artifact"] == "swiss_1500_now_global_slow_v1.npz"
    assert payload["index_coverage"]["reliable_history_start"] == 1500
    assert payload["index_coverage"]["index_coverage_status"] == "full"
    assert payload["index_coverage"]["history_window_label"] == "mixed_reliable"
    assert payload["index_coverage"]["index_window_start"].startswith("1500-01-01")


def test_resonance_search_accepts_reliable_1500_index_for_pre_1900_request(
    tmp_path: Path,
) -> None:
    save_sparse_synthetic_index(
        tmp_path / "swiss_1500_now_global_slow_v1.npz",
        (
            datetime(1500, 1, 1, tzinfo=UTC),
            datetime(1689, 7, 14, tzinfo=UTC),
            datetime(1789, 7, 14, tzinfo=UTC),
        ),
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "1789-07-14T00:00:00Z",
            "lookback_years": 100,
            "lookahead_years": 0,
            "top_k": 3,
            "max_episodes": 3,
            "index_file": "swiss_1500_now_global_slow_v1.npz",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_coverage"]["index_coverage_status"] == "full"
    assert payload["index_coverage"]["history_window_label"] == "reliable_early_modern"
    assert payload["episodes"]


def test_resonance_search_rejects_1900_index_for_early_modern_request(
    tmp_path: Path,
) -> None:
    save_sparse_synthetic_index(
        tmp_path / "swiss_1900_now_global_slow_v1.npz",
        (
            datetime(1900, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2026-01-01T00:00:00Z",
            "lookback_years": 426,
            "lookahead_years": 0,
            "index_file": "swiss_1900_now_global_slow_v1.npz",
        },
    )

    assert response.status_code == 400
    assert "Index does not cover request start" in response.json()["detail"]


def test_resonance_search_marks_pre_1500_overlap_as_partial(tmp_path: Path) -> None:
    save_sparse_synthetic_index(
        tmp_path / "swiss_1500_now_global_slow_v1.npz",
        (
            datetime(1500, 1, 1, tzinfo=UTC),
            datetime(1510, 1, 1, tzinfo=UTC),
        ),
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "1490-01-01T00:00:00Z",
            "lookback_years": 10,
            "lookahead_years": 20,
            "top_k": 2,
            "max_episodes": 2,
            "index_file": "swiss_1500_now_global_slow_v1.npz",
        },
    )

    assert response.status_code == 200
    coverage = response.json()["index_coverage"]
    assert coverage["index_coverage_status"] == "partial"
    assert coverage["warning"]


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
    assert "Index does not cover request start" in response.json()["detail"]


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


def test_broad_context_events_are_split_from_matched_events() -> None:
    events = tuple(
        event
        for event in load_curated_events()
        if event.id
        in {
            "evt_financial_crisis_2007_2008",
            "evt_globalization_era",
            "evt_neoliberal_turn",
        }
    )

    matched_events, context_events = _split_context_events(events)

    assert {event.id for event in matched_events} == {"evt_financial_crisis_2007_2008"}
    assert {event.id for event in context_events} == {
        "evt_globalization_era",
        "evt_neoliberal_turn",
    }
