from __future__ import annotations

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from services.api.app import (
    ActiveRegimeWindow,
    _active_cycle_windows,
    _build_provider,
    _classify_events_for_episode_window,
    _event_temporal_match,
    _historical_episodes_from_points,
    _split_context_events,
    _split_local_and_historical_points,
    create_app,
)
from services.api.schemas import ResonanceSearchRequest
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.historical.events import HistoricalEvent
from services.resonance.episode_clustering import CandidatePoint
from services.resonance.index_builder import BuiltIndex, IndexRow, build_weekly_index
from services.resonance.index_store import save_built_index
from services.resonance.vectorizer import GLOBAL_SLOW_VECTOR_VERSION, vectorize_global_slow

AUTH_HEADERS = {"x-astro-global-session": "test-token"}


def historical_event(
    *,
    event_id: str,
    title: str = "Test event",
    display_date: str,
    start_year: int,
    end_year: int | None = None,
    event_kind: str = "instant_event",
) -> HistoricalEvent:
    return HistoricalEvent(
        id=event_id,
        title=title,
        display_date=display_date,
        start_astro_year=start_year,
        end_astro_year=end_year if end_year is not None else start_year,
        category="test",
        event_kind=event_kind,
        region="Global",
        geo_scope="global",
        source_url="https://example.com/event",
        confidence_score=0.8,
    )


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


def save_scored_synthetic_index(
    path: Path,
    *,
    query_dt: datetime,
    scored_datetimes: tuple[tuple[datetime, float], ...],
) -> None:
    query_vector = vectorize_global_slow(
        SyntheticEphemerisProvider().compute_state(query_dt)
    ).vector
    unit_query = query_vector / np.linalg.norm(query_vector)
    basis = np.zeros_like(unit_query)
    basis[0] = 1.0
    orthogonal = basis - float(np.dot(basis, unit_query)) * unit_query
    if np.linalg.norm(orthogonal) == 0.0:
        basis[1] = 1.0
        orthogonal = basis - float(np.dot(basis, unit_query)) * unit_query
    unit_orthogonal = orthogonal / np.linalg.norm(orthogonal)
    rows = tuple(
        IndexRow(row_index=index, datetime_utc=dt, julian_day_ut=float(index + 1))
        for index, (dt, _score) in enumerate(scored_datetimes)
    )
    matrix = np.asarray(
        [
            score * unit_query + np.sqrt(max(0.0, 1.0 - score**2)) * unit_orthogonal
            for _dt, score in scored_datetimes
        ],
        dtype=np.float64,
    )
    save_built_index(
        BuiltIndex(matrix=matrix, rows=rows),
        path,
        profile_id="global_slow_v1",
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        provider="synthetic-dev",
        step_days=7,
    )


def test_historical_episode_pool_backfills_independent_periods() -> None:
    request = ResonanceSearchRequest(
        date_utc=datetime(2026, 5, 25, tzinfo=UTC),
        top_k=4,
        max_episodes=3,
        historical_analogue_mode=True,
    )
    points = [
        CandidatePoint(date=date(2015, 4, 20), score=0.90, row_index=0),
        CandidatePoint(date=date(2015, 5, 1), score=0.89, row_index=1),
        CandidatePoint(date=date(2013, 4, 22), score=0.88, row_index=2),
        CandidatePoint(date=date(2013, 5, 1), score=0.87, row_index=3),
        CandidatePoint(date=date(1987, 3, 9), score=0.70, row_index=4),
        CandidatePoint(date=date(1987, 4, 1), score=0.69, row_index=5),
    ]

    episodes = _historical_episodes_from_points(points=points, request=request)

    assert [episode.best_date.year for episode in episodes] == [2015, 2013, 1987]
    assert episodes[0].period_start == date(2015, 4, 20)
    assert episodes[1].period_start == date(2013, 4, 22)


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
    assert "http://127.0.0.1:5174" in payload["security"]["cors_allowed_origins"]
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


def test_resonance_compare_presets_require_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/resonance/compare/presets")

    assert response.status_code == 401


def test_resonance_compare_presets_are_backend_authored_from_curated_events() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/resonance/compare/presets", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "astro-global-core"
    assert payload["provider"] == "swiss"
    assert payload["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert payload["date_policy"] == "curated_start_year_to_utc_year_start"
    assert len(payload["presets"]) >= 3
    presets = {preset["preset_id"]: preset for preset in payload["presets"]}
    revolutionary = presets["revolutionary_wave_1789_1848"]
    assert revolutionary["left_event"]["event_id"] == "evt_french_revolution"
    assert revolutionary["right_event"]["event_id"] == "evt_revolutions_1848"
    assert revolutionary["left_event"]["date_utc"] == "1789-01-01T00:00:00Z"
    assert revolutionary["right_event"]["date_precision"] == "year_start_anchor"
    request = revolutionary["compare_request"]
    assert request["provider"] == "swiss"
    assert request["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert request["left_date_utc"] == revolutionary["left_event"]["date_utc"]
    assert request["right_date_utc"] == revolutionary["right_event"]["date_utc"]
    assert any("not a prediction" in warning for warning in revolutionary["warnings"])


def test_article_seeds_require_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/articles/seeds")

    assert response.status_code == 401


def test_article_seeds_are_seed_only_backend_contract() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/articles/seeds", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "astro-global-core"
    assert payload["provider"] == "swiss"
    assert payload["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert payload["content_policy"] == "seed_only_no_generated_article_text"
    assert len(payload["seeds"]) >= 3
    first_seed = payload["seeds"][0]
    assert first_seed["editorial_status"] == "seed_only_not_article"
    assert first_seed["seed_kind"] == "compare_research_seed"
    assert first_seed["compare_preset_id"] == "revolutionary_wave_1789_1848"
    assert first_seed["source_event_ids"] == [
        "evt_french_revolution",
        "evt_revolutions_1848",
    ]
    assert first_seed["compare_request"]["provider"] == "swiss"
    assert first_seed["compare_request"]["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert "POST /resonance/compare" in first_seed["allowed_next_api_calls"]
    assert any("not generated articles" in warning for warning in first_seed["warnings"])
    assert "article_body" not in first_seed
    assert "generated_text" not in first_seed


def test_timeline_seeds_require_session_token() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/timeline/seeds")

    assert response.status_code == 401


def test_timeline_seeds_are_backend_authored_search_starters() -> None:
    client = TestClient(create_app(session_token="test-token"))

    response = client.get("/timeline/seeds", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "astro-global-core"
    assert payload["provider"] == "swiss"
    assert payload["index_file"] == "swiss_1500_now_global_slow_v1.npz"
    assert payload["date_policy"] == "curated_start_year_to_utc_year_start"
    assert payload["selection_policy"] == "backend_featured_reliable_history_seed_set"
    assert len(payload["seeds"]) >= 10
    seeds = {seed["event_id"]: seed for seed in payload["seeds"]}
    french_revolution = seeds["evt_french_revolution"]
    assert french_revolution["seed_id"] == "timeline_evt_french_revolution"
    assert french_revolution["date_utc"] == "1789-01-01T00:00:00Z"
    assert french_revolution["date_precision"] == "year_start_anchor"
    assert french_revolution["search_request"]["provider"] == "swiss"
    assert (
        french_revolution["search_request"]["index_file"]
        == "swiss_1500_now_global_slow_v1.npz"
    )
    assert (
        french_revolution["search_request"]["date_utc"]
        == french_revolution["date_utc"]
    )
    assert "POST /resonance/search" in french_revolution["allowed_next_api_calls"]
    assert any("not a prediction" in warning for warning in french_revolution["warnings"])
    assert "generated_text" not in french_revolution


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


def test_resonance_search_allows_query_after_persistent_index_end(
    tmp_path: Path,
) -> None:
    built = build_weekly_index(
        SyntheticEphemerisProvider(),
        datetime_from_iso("2025-05-22T12:00:00+00:00"),
        datetime_from_iso("2026-05-22T12:00:00+00:00"),
        step_days=7,
    )
    save_built_index(
        built,
        tmp_path / "current_index.npz",
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
            "date_utc": "2026-06-15T00:00:00Z",
            "lookback_years": 1,
            "lookahead_years": 0,
            "top_k": 10,
            "max_episodes": 3,
            "index_file": "current_index.npz",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_source"] == "persistent_npz"
    assert payload["index_coverage"]["index_coverage_status"] == "partial"
    assert payload["query_datetime_utc"].startswith("2026-06-15")


def test_resonance_search_historical_mode_separates_local_resonance(
    tmp_path: Path,
) -> None:
    query_dt = datetime(2011, 12, 31, 22, tzinfo=UTC)
    save_scored_synthetic_index(
        tmp_path / "historical_mode.npz",
        query_dt=query_dt,
        scored_datetimes=(
            (datetime(1991, 12, 31, tzinfo=UTC), 0.10),
            (datetime(1999, 2, 15, tzinfo=UTC), 0.72),
            (datetime(2006, 11, 27, tzinfo=UTC), 0.71),
            (datetime(2011, 12, 26, tzinfo=UTC), 0.99),
            (datetime(2011, 12, 31, tzinfo=UTC), 0.98),
            (datetime(2012, 1, 4, tzinfo=UTC), 0.97),
            (datetime(2012, 12, 31, tzinfo=UTC), 0.05),
        ),
    )
    client = TestClient(create_app(session_token="test-token", vector_index_root=tmp_path))

    response = client.post(
        "/resonance/search",
        headers=AUTH_HEADERS,
        json={
            "date_utc": "2011-12-31T22:00:00Z",
            "lookback_years": 20,
            "lookahead_years": 1,
            "top_k": 7,
            "max_episodes": 3,
            "index_file": "historical_mode.npz",
            "historical_analogue_mode": True,
            "local_resonance_window_days": 365,
            "historical_analogue_min_year_gap": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["local_resonance"]["best_date"] == "2011-12-26"
    assert 5 in payload["local_resonance"]["row_indices"]
    assert payload["analogue_policy"]["local_resonance_excluded"] is True
    assert payload["historical_analogues"] == payload["episodes"]
    assert payload["nearby_matches"]
    assert payload["local_resonance_window"] == payload["nearby_matches"]
    assert payload["episodes"]
    analogue_dates = {episode["best_date"] for episode in payload["historical_analogues"]}
    assert "2011-12-26" not in analogue_dates
    assert "2012-01-04" not in analogue_dates
    assert all(
        not episode["best_date"].startswith(("2011-", "2012-"))
        for episode in payload["historical_analogues"]
    )
    assert any(episode["best_date"].startswith("1999-") for episode in payload["episodes"])
    assert "active_cycle_windows" in payload
    assert payload["active_cycle_windows"] == payload["regime_cycle_windows"]


def test_active_cycle_windows_scan_start_peak_end_for_2026_swiss() -> None:
    if importlib.util.find_spec("swisseph") is None:
        pytest.skip("Swiss Ephemeris is not installed.")

    provider = _build_provider("swiss")
    query_dt = datetime(2026, 5, 24, tzinfo=UTC)
    query_vector = vectorize_global_slow(provider.compute_state(query_dt))
    windows = _active_cycle_windows(
        provider=provider,
        query_dt=query_dt,
        primary_cycles=query_vector.cycle_strength_debug_json["primary_cycles"],
        supporting_cycles=query_vector.cycle_strength_debug_json["supporting_cycles"],
        enabled=True,
    )

    windows_by_label = {window.label: window for window in windows}
    for expected_label in (
        "Neptune-Uranus sextile",
        "Pluto-Uranus trine",
        "Neptune-Pluto sextile",
    ):
        window = windows_by_label[expected_label]
        assert window.start_date <= query_dt.date() <= window.end_date
        assert window.peak_date is not None
        assert window.start_date <= window.peak_date <= window.end_date
        assert window.orb_at_query is not None
        assert window.confidence_scope == "sampled_weekly_from_ephemeris"


def test_historical_split_excludes_same_active_regime_beyond_same_year() -> None:
    request = ResonanceSearchRequest(
        date_utc=datetime(2026, 5, 24, tzinfo=UTC),
        historical_analogue_mode=True,
        exclude_same_calendar_year=True,
        local_resonance_window_days=365,
        historical_analogue_min_year_gap=0,
    )
    points = [
        CandidatePoint(date=date(2024, 6, 17), score=0.95, row_index=1),
        CandidatePoint(date=date(2028, 2, 1), score=0.93, row_index=2),
        CandidatePoint(date=date(2015, 4, 20), score=0.75, row_index=3),
    ]
    active_windows = [
        ActiveRegimeWindow(
            driver_id="sign:Pluto:Aquarius",
            driver_type="sign_regime",
            label="Pluto in Aquarius",
            start_date=date(2024, 1, 20),
            end_date=date(2043, 3, 8),
            source="query_slow_body_sign",
        ),
        ActiveRegimeWindow(
            driver_id="cycle:Saturn-Neptune:conjunction",
            driver_type="cycle",
            label="Saturn-Neptune conjunction",
            start_date=date(2025, 3, 1),
            end_date=date(2028, 2, 29),
            source="query_active_cycle",
        ),
    ]

    local_points, historical_points = _split_local_and_historical_points(
        points=points,
        query_dt=request.date_utc,
        request=request,
        active_regime_windows=active_windows,
    )

    assert {point.date for point in local_points} == {date(2024, 6, 17), date(2028, 2, 1)}
    assert [point.date for point in historical_points] == [date(2015, 4, 20)]


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
    assert "matched_events" in payload["episodes"][0]
    assert payload["episodes"][0]["context_events"]
    assert "omitted_point_events" in payload["episodes"][0]
    assert payload["episodes"][0]["context_events"][0]["event_id"]
    assert payload["episodes"][0]["context_events"][0]["sources"]
    first_event_sources = payload["episodes"][0]["context_events"][0]["sources"]
    first_event_source_qualities = {source["source_quality"] for source in first_event_sources}
    all_event_source_qualities = {
        source["source_quality"]
        for event in payload["episodes"][0]["context_events"]
        for source in event["sources"]
    }
    assert "wikidata_seed" in first_event_source_qualities
    assert first_event_source_qualities - {"wikidata_seed"}
    assert all_event_source_qualities & {"encyclopedic", "institutional", "primary"}
    assert payload["episodes"][0]["context_events"][0]["temporal_relation"]
    assert payload["episodes"][0]["context_events"][0]["temporal_match_score"] < 0.8
    assert payload["episodes"][0]["event_coverage"]["events_found"] == len(
        payload["episodes"][0]["matched_events"]
    )
    assert payload["episodes"][0]["score_breakdown"]["cycle_power_score"] > 0
    assert payload["episodes"][0]["score_breakdown"]["label"] == "strong"
    assert payload["episodes"][0]["narrative_confidence"]["narrative_confidence"] >= 0


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


def test_episode_event_classification_requires_exact_window_overlap() -> None:
    events = (
        historical_event(
            event_id="evt_inside_exact",
            title="Inside exact event",
            display_date="2015-05-10",
            start_year=2015,
        ),
        historical_event(
            event_id="evt_outside_exact",
            title="Outside exact event",
            display_date="2015-12-12",
            start_year=2015,
        ),
        historical_event(
            event_id="evt_year_only",
            title="Year-only event",
            display_date="2015",
            start_year=2015,
        ),
        historical_event(
            event_id="evt_broad_range",
            title="Broad range event",
            display_date="2014-2016",
            start_year=2014,
            end_year=2016,
            event_kind="crisis",
        ),
    )

    matched_events, context_events, temporal_matches = _classify_events_for_episode_window(
        events=events,
        window_start=date(2015, 4, 20),
        window_end=date(2015, 6, 8),
        limit=4,
    )

    assert {event.id for event in matched_events} == {"evt_inside_exact"}
    assert {event.id for event in context_events} == {
        "evt_year_only",
        "evt_broad_range",
    }
    assert temporal_matches["evt_inside_exact"].relation == "exact_date_in_window"
    assert temporal_matches["evt_outside_exact"].relation == "outside_window"
    assert temporal_matches["evt_year_only"].precision == "approximate_year"


def test_temporal_match_scores_overlapping_exact_ranges() -> None:
    event = historical_event(
        event_id="evt_exact_range",
        title="Exact range event",
        display_date="2015-04-01 - 2015-04-30",
        start_year=2015,
    )

    temporal_match = _event_temporal_match(
        event=event,
        window_start=date(2015, 4, 20),
        window_end=date(2015, 6, 8),
    )

    assert temporal_match.precision == "exact_date_range"
    assert temporal_match.relation == "exact_range_overlaps_window"
    assert temporal_match.score >= 0.8
