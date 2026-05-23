from __future__ import annotations

import importlib.util
import os
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ephemeris.provider import PlanetaryPosition
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.context import is_broad_context_event_id
from services.historical.coverage import build_coverage_report
from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    event_sources_from_events,
    load_curated_event_sources,
    load_curated_events,
)
from services.historical.event_query import (
    DEFAULT_DUCKDB_PATH,
    find_event_selection_overlapping_years,
    find_events_overlapping_years,
    find_sources_for_event_ids,
)
from services.narrative.confidence import build_narrative_confidence
from services.narrative.deterministic_summary import (
    DeterministicSummary,
    build_deterministic_summary,
)
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import BuiltIndex, build_weekly_index
from services.resonance.index_store import load_built_index
from services.resonance.scoring import build_resonance_strength_breakdown
from services.resonance.vectorizer import (
    GLOBAL_SLOW_PROFILE_ID,
    GLOBAL_SLOW_VECTOR_VERSION,
    vectorize_global_slow,
)

MAX_TOP_K = 100
MAX_EPISODES = 20
MAX_EVENTS_PER_EPISODE = 12
MAX_EVENTS_WINDOW = 100
DEFAULT_VECTOR_INDEX_ROOT = Path("data/vectors")
SESSION_TOKEN_HEADER = "x-astro-global-session"
SESSION_TOKEN_ENV = "ASTRO_GLOBAL_SESSION_TOKEN"
RUNTIME_ENV_ENV = "ASTRO_GLOBAL_ENV"
CORS_ORIGINS_ENV = "ASTRO_GLOBAL_CORS_ORIGINS"
RATE_LIMIT_ENABLED_ENV = "ASTRO_GLOBAL_RATE_LIMIT_ENABLED"
RATE_LIMIT_PER_MINUTE_ENV = "ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE"
MAX_REQUEST_BYTES_ENV = "ASTRO_GLOBAL_MAX_REQUEST_BYTES"
DEFAULT_DEV_SESSION_TOKEN = "dev-local-token"
DEFAULT_REQUIRED_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_MAX_REQUEST_BYTES = 65536
RELIABLE_HISTORY_START_YEAR = 1500
RELIABLE_MODERN_START_YEAR = 1900
RELIABLE_HISTORY_END_YEAR = 2026
RELIABLE_HISTORY_START_UTC = datetime(RELIABLE_HISTORY_START_YEAR, 1, 1, tzinfo=UTC)
LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


class ResonanceSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_utc: datetime
    profile_id: str = GLOBAL_SLOW_PROFILE_ID
    lookback_years: int = Field(default=10, ge=1, le=600)
    lookahead_years: int = Field(default=2, ge=0, le=50)
    step_days: int = Field(default=7, ge=1, le=31)
    top_k: int = Field(default=30, ge=1, le=MAX_TOP_K)
    max_episodes: int = Field(default=8, ge=1, le=MAX_EPISODES)
    events_per_episode: int = Field(default=6, ge=0, le=MAX_EVENTS_PER_EPISODE)
    event_window_years: int = Field(default=1, ge=0, le=25)
    provider: str = "synthetic"
    index_file: str | None = None

    @field_validator("date_utc")
    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ResonanceCompareRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_date_utc: datetime
    right_date_utc: datetime
    profile_id: str = GLOBAL_SLOW_PROFILE_ID
    lookback_years: int = Field(default=120, ge=1, le=600)
    lookahead_years: int = Field(default=0, ge=0, le=50)
    step_days: int = Field(default=7, ge=1, le=31)
    top_k: int = Field(default=30, ge=1, le=MAX_TOP_K)
    max_episodes: int = Field(default=5, ge=1, le=MAX_EPISODES)
    events_per_episode: int = Field(default=6, ge=0, le=MAX_EVENTS_PER_EPISODE)
    event_window_years: int = Field(default=1, ge=0, le=25)
    provider: str = "synthetic"
    index_file: str | None = None

    @field_validator("left_date_utc", "right_date_utc")
    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class SkyAtDateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_utc: datetime
    provider: str = "synthetic"

    @field_validator("date_utc")
    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PlanetaryPositionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    body: str
    longitude_deg: float
    latitude_deg: float
    distance_au: float | None
    speed_longitude_deg_per_day: float
    retrograde: bool


class SkyStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    datetime_utc: str
    julian_day_ut: float
    astro_profile_id: str
    ephemeris_version: str
    flags: tuple[str, ...]
    positions: list[PlanetaryPositionResponse]


class ResonanceEpisodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    best_date: str
    best_score: float
    best_percentile: float
    row_indices: tuple[int, ...]
    matched_events: list[HistoricalEventResponse]
    context_events: list[HistoricalEventResponse] = Field(default_factory=list)
    omitted_point_events: list[HistoricalEventResponse] = Field(default_factory=list)
    event_coverage: EventCoverageResponse
    score_breakdown: ScoreBreakdownResponse
    narrative_confidence: NarrativeConfidenceResponse


class HistoricalEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    event_kind: str
    is_ongoing: bool = False
    end_year_policy: str = "explicit"
    region: str
    geo_scope: str
    source_url: str
    confidence_score: float
    sources: list[EventSourceResponse]


class EventSourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_type: str
    source_name: str
    source_url: str
    source_quality: str
    source_precision: str


class EventCoverageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    events_found: int
    regions: dict[str, int]
    categories: dict[str, int]
    event_kinds: dict[str, int] = Field(default_factory=dict)
    ongoing_events_count: int = 0
    dominant_region_bias: str | None
    warning: str | None


class NarrativeConfidenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_coverage_score: float
    source_quality_score: float
    evidence_confidence: float
    narrative_confidence: float


class ScoreBreakdownResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    structural_similarity: float
    cycle_power_score: float
    rarity_adjusted_percentile: float
    planetary_resonance_score: float
    label: str
    primary_cycle_count: int
    strongest_primary_contribution: float
    rare_configuration: bool
    insufficient_comparable_history: bool


class IndexCoverageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    reliable_history_start: int
    reliable_history_end: int
    index_window_start: str
    index_window_end: str
    request_window_start: str
    request_window_end: str
    index_coverage_status: str
    history_window_label: str
    warning: str | None = None


class ResonanceSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    vector_version: str
    provider: str
    query_datetime_utc: str
    index_start_utc: str
    index_end_utc: str
    index_source: str
    index_artifact: str | None
    index_rows: int
    index_coverage: IndexCoverageResponse
    primary_cycles: list[dict[str, object]]
    supporting_cycles: list[dict[str, object]]
    episodes: list[ResonanceEpisodeResponse]
    deterministic_summary: DeterministicSummary


class ResonanceCompareResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    vector_version: str
    provider: str
    left: ResonanceSearchResponse
    right: ResonanceSearchResponse
    query_vector_similarity: float
    shared_primary_cycles: tuple[str, ...]
    shared_matched_event_ids: tuple[str, ...]
    shared_context_event_ids: tuple[str, ...]
    left_only_matched_event_ids: tuple[str, ...]
    right_only_matched_event_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    deterministic_summary: str


class EventsWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_astro_year: int
    end_astro_year: int
    limit: int
    events: list[HistoricalEventResponse]
    event_coverage: EventCoverageResponse


class ProviderStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_provider: str
    synthetic_available: bool
    swiss_available: bool
    swiss_import_error: str | None


class DataStoreStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    duckdb_path: str
    duckdb_exists: bool
    curated_events_path: str
    curated_events_count: int
    curated_event_sources_count: int
    event_kind_counts: dict[str, int]
    source_quality_counts: dict[str, int]
    source_precision_counts: dict[str, int]
    ongoing_events_count: int
    ongoing_event_ids: tuple[str, ...]
    events_without_curated_sources: tuple[str, ...]
    weak_precision_events_without_direct_backup: tuple[str, ...]
    fallback_to_curated_csv: bool


class ApiSecurityStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime_environment: str
    auth_required: bool
    token_header: str
    cors_allowed_origins: tuple[str, ...]
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    max_request_bytes: int


class DataStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    profiles: tuple[str, ...]
    vector_versions: tuple[str, ...]
    providers: ProviderStatusResponse
    data_store: DataStoreStatusResponse
    security: ApiSecurityStatusResponse


class TodaySnapshotResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    snapshot_date_utc: str
    generated_at_utc: str
    expires_at_utc: str
    cache_key: str
    profile_id: str
    provider: str
    index_file: str
    reliable_history_start: int
    reliable_history_end: int
    history_window_label: str
    recommended_search_request: ResonanceSearchRequest
    ui_contract: tuple[str, ...]
    warnings: tuple[str, ...]


class ReadinessCheckResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: str
    detail: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    status: str
    checked_at_utc: str
    required_index_file: str
    checks: list[ReadinessCheckResponse]


class FixedWindowRateLimiter:
    def __init__(
        self,
        *,
        limit_per_window: int,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self.limit_per_window = limit_per_window
        self.window_seconds = window_seconds
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        window_start, count = self._windows.get(key, (now, 0))
        elapsed = now - window_start
        if elapsed >= self.window_seconds:
            window_start = now
            elapsed = 0.0
            count = 0

        count += 1
        self._windows[key] = (window_start, count)
        retry_after_seconds = max(1, int(self.window_seconds - elapsed))
        return count <= self.limit_per_window, retry_after_seconds


def create_app(
    event_db_path: Path | str = DEFAULT_DUCKDB_PATH,
    *,
    vector_index_root: Path | str = DEFAULT_VECTOR_INDEX_ROOT,
    required_index_file: str = DEFAULT_REQUIRED_INDEX_FILE,
    session_token: str | None = None,
    cors_allowed_origins: tuple[str, ...] | None = None,
    rate_limit_enabled: bool | None = None,
    rate_limit_per_minute: int | None = None,
    max_request_bytes: int | None = None,
    require_auth: bool = True,
) -> FastAPI:
    app = FastAPI(title="Astro Global Core API", version="0.1.0")
    runtime_environment = _runtime_environment()
    resolved_session_token = _resolve_api_session_token(
        explicit_session_token=session_token,
        runtime_environment=runtime_environment,
        require_auth=require_auth,
    )
    resolved_cors_allowed_origins = _resolve_cors_allowed_origins(
        explicit_origins=cors_allowed_origins,
        runtime_environment=runtime_environment,
    )
    resolved_rate_limit_enabled = _resolve_rate_limit_enabled(
        explicit_enabled=rate_limit_enabled,
        runtime_environment=runtime_environment,
    )
    resolved_rate_limit_per_minute = _resolve_rate_limit_per_minute(
        explicit_limit=rate_limit_per_minute,
    )
    resolved_max_request_bytes = _resolve_max_request_bytes(
        explicit_max_request_bytes=max_request_bytes,
    )
    app.state.session_token = resolved_session_token
    app.state.require_auth = require_auth
    app.state.runtime_environment = runtime_environment
    app.state.rate_limit_enabled = resolved_rate_limit_enabled
    app.state.rate_limit_per_minute = resolved_rate_limit_per_minute
    app.state.max_request_bytes = resolved_max_request_bytes
    app.state.today_snapshot_cache = {}
    app.state.rate_limiter = FixedWindowRateLimiter(
        limit_per_window=resolved_rate_limit_per_minute,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["authorization", "content-type", SESSION_TOKEN_HEADER],
    )

    @app.middleware("http")
    async def require_session_token(request: Request, call_next: object) -> object:
        if not app.state.require_auth or request.url.path == "/health":
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if _request_session_token(request) != app.state.session_token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Astro Global session token."},
            )
        request_size_limit_response = _request_size_limit_response(
            request,
            max_request_bytes=app.state.max_request_bytes,
        )
        if request_size_limit_response is not None:
            return request_size_limit_response
        if app.state.rate_limit_enabled and not _is_unmetered_path(request.url.path):
            allowed, retry_after_seconds = app.state.rate_limiter.hit(
                _rate_limit_key(request)
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Astro Global API rate limit exceeded.",
                        "retry_after_seconds": retry_after_seconds,
                    },
                    headers={"Retry-After": str(retry_after_seconds)},
                )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "astro-global-core"}

    @app.get("/data/status", response_model=DataStatusResponse)
    def data_status() -> DataStatusResponse:
        return _data_status_response(
            event_db_path=event_db_path,
            auth_required=app.state.require_auth,
            cors_allowed_origins=resolved_cors_allowed_origins,
            runtime_environment=runtime_environment,
            rate_limit_enabled=app.state.rate_limit_enabled,
            rate_limit_per_minute=app.state.rate_limit_per_minute,
            max_request_bytes=app.state.max_request_bytes,
        )

    @app.get("/today", response_model=TodaySnapshotResponse)
    def today(response: Response) -> TodaySnapshotResponse:
        snapshot = _today_snapshot_response(
            cache=app.state.today_snapshot_cache,
            required_index_file=required_index_file,
            now_utc=datetime.now(UTC),
        )
        response.headers["Cache-Control"] = "public, max-age=300"
        response.headers["X-Astro-Global-Snapshot-Date"] = snapshot.snapshot_date_utc
        return snapshot

    @app.get("/readiness", response_model=ReadinessResponse)
    def readiness(response: Response) -> ReadinessResponse:
        readiness_response = _readiness_response(
            event_db_path=event_db_path,
            vector_index_root=vector_index_root,
            required_index_file=required_index_file,
        )
        if readiness_response.status != "ready":
            response.status_code = 503
        return readiness_response

    @app.get("/sky/current", response_model=SkyStateResponse)
    def sky_current(provider: str = "synthetic") -> SkyStateResponse:
        return _sky_state_response(datetime.now(UTC), provider)

    @app.post("/sky/at-date", response_model=SkyStateResponse)
    def sky_at_date(request: SkyAtDateRequest) -> SkyStateResponse:
        return _sky_state_response(request.date_utc, request.provider)

    @app.get("/events/window", response_model=EventsWindowResponse)
    def events_window(
        start_astro_year: int = Query(...),
        end_astro_year: int = Query(...),
        limit: int = Query(25, ge=0, le=MAX_EVENTS_WINDOW),
    ) -> EventsWindowResponse:
        if end_astro_year < start_astro_year:
            raise HTTPException(
                status_code=400,
                detail="end_astro_year must be >= start_astro_year.",
            )
        events = find_events_overlapping_years(
            start_astro_year=start_astro_year,
            end_astro_year=end_astro_year,
            db_path=event_db_path,
            limit=limit,
        )
        sources_by_event = _sources_by_event(
            event_ids=tuple(event.id for event in events),
            event_db_path=event_db_path,
        )
        coverage = build_coverage_report(events)
        return EventsWindowResponse(
            start_astro_year=start_astro_year,
            end_astro_year=end_astro_year,
            limit=limit,
            events=[
                _historical_event_response(event=event, sources=sources_by_event.get(event.id, []))
                for event in events
            ],
            event_coverage=EventCoverageResponse(**coverage.model_dump()),
        )

    @app.post("/resonance/search", response_model=ResonanceSearchResponse)
    def resonance_search(request: ResonanceSearchRequest) -> ResonanceSearchResponse:
        return _resonance_search_response(
            request=request,
            event_db_path=event_db_path,
            vector_index_root=vector_index_root,
        )

    @app.post("/resonance/compare", response_model=ResonanceCompareResponse)
    def resonance_compare(request: ResonanceCompareRequest) -> ResonanceCompareResponse:
        left_request = _compare_side_search_request(request, request.left_date_utc)
        right_request = _compare_side_search_request(request, request.right_date_utc)
        left = _resonance_search_response(
            request=left_request,
            event_db_path=event_db_path,
            vector_index_root=vector_index_root,
        )
        right = _resonance_search_response(
            request=right_request,
            event_db_path=event_db_path,
            vector_index_root=vector_index_root,
        )
        return _resonance_compare_response(
            request=request,
            left=left,
            right=right,
        )

    return app


def _resonance_search_response(
    *,
    request: ResonanceSearchRequest,
    event_db_path: Path | str,
    vector_index_root: Path | str,
) -> ResonanceSearchResponse:
    if request.profile_id != GLOBAL_SLOW_PROFILE_ID:
        raise HTTPException(status_code=400, detail="Only global_slow_v1 is available.")

    provider = _build_provider(request.provider)
    query_dt = request.date_utc
    start_utc = query_dt - timedelta(days=365 * request.lookback_years)
    end_utc = query_dt + timedelta(days=365 * request.lookahead_years)
    query_state = provider.compute_state(query_dt)
    query_vector = vectorize_global_slow(query_state)
    built_index, index_source, index_artifact, index_window_start, index_window_end = (
        _load_or_build_index(
            request=request,
            provider=provider,
            start_utc=start_utc,
            end_utc=end_utc,
            ephemeris_version=query_state.ephemeris_version,
            vector_index_root=vector_index_root,
        )
    )
    index_coverage = _index_coverage_response(
        index_window_start=index_window_start,
        index_window_end=index_window_end,
        request_window_start=start_utc,
        request_window_end=end_utc,
    )
    hits = exact_search(built_index.matrix, query_vector.vector, top_k=request.top_k)
    points = []
    for hit in hits:
        row = built_index.rows[hit.row_index]
        points.append(
            CandidatePoint(
                date=row.datetime_utc.date(),
                score=hit.score,
                row_index=row.row_index,
                percentile=hit.percentile,
            )
        )
    episodes = cluster_candidate_points(points)[: request.max_episodes]
    primary_cycles = query_vector.cycle_strength_debug_json["primary_cycles"]
    supporting_cycles = query_vector.cycle_strength_debug_json["supporting_cycles"]

    episode_responses = [
        _episode_response(
            episode=episode,
            event_db_path=event_db_path,
            event_window_years=request.event_window_years,
            events_per_episode=request.events_per_episode,
            index_rows=len(built_index.rows),
            primary_cycles=primary_cycles,
        )
        for episode in episodes
    ]

    return ResonanceSearchResponse(
        profile_id=query_vector.profile_id,
        vector_version=query_vector.vector_version,
        provider=query_state.ephemeris_version,
        query_datetime_utc=query_state.datetime_utc.isoformat(),
        index_start_utc=start_utc.isoformat(),
        index_end_utc=end_utc.isoformat(),
        index_source=index_source,
        index_artifact=index_artifact,
        index_rows=len(built_index.rows),
        index_coverage=index_coverage,
        primary_cycles=primary_cycles,
        supporting_cycles=supporting_cycles,
        episodes=episode_responses,
        deterministic_summary=build_deterministic_summary(
            profile_id=query_vector.profile_id,
            query_datetime_utc=query_state.datetime_utc.isoformat(),
            primary_cycles=primary_cycles,
            supporting_cycles=supporting_cycles,
            episodes=episode_responses,
        ),
    )


def _compare_side_search_request(
    request: ResonanceCompareRequest,
    date_utc: datetime,
) -> ResonanceSearchRequest:
    return ResonanceSearchRequest(
        date_utc=date_utc,
        profile_id=request.profile_id,
        lookback_years=request.lookback_years,
        lookahead_years=request.lookahead_years,
        step_days=request.step_days,
        top_k=request.top_k,
        max_episodes=request.max_episodes,
        events_per_episode=request.events_per_episode,
        event_window_years=request.event_window_years,
        provider=request.provider,
        index_file=request.index_file,
    )


def _resonance_compare_response(
    *,
    request: ResonanceCompareRequest,
    left: ResonanceSearchResponse,
    right: ResonanceSearchResponse,
) -> ResonanceCompareResponse:
    provider = _build_provider(request.provider)
    left_vector = vectorize_global_slow(provider.compute_state(request.left_date_utc)).vector
    right_vector = vectorize_global_slow(provider.compute_state(request.right_date_utc)).vector
    shared_primary_cycles = _shared_cycle_labels(left.primary_cycles, right.primary_cycles)
    shared_matched_event_ids = _shared_event_ids(left.episodes, right.episodes, "matched_events")
    shared_context_event_ids = _shared_event_ids(left.episodes, right.episodes, "context_events")
    left_matched_event_ids = _episode_event_ids(left.episodes, "matched_events")
    right_matched_event_ids = _episode_event_ids(right.episodes, "matched_events")
    warnings = _compare_warnings(left, right)
    similarity = _cosine_similarity(left_vector, right_vector)
    return ResonanceCompareResponse(
        profile_id=left.profile_id,
        vector_version=left.vector_version,
        provider=left.provider,
        left=left,
        right=right,
        query_vector_similarity=similarity,
        shared_primary_cycles=shared_primary_cycles,
        shared_matched_event_ids=shared_matched_event_ids,
        shared_context_event_ids=shared_context_event_ids,
        left_only_matched_event_ids=tuple(
            event_id
            for event_id in left_matched_event_ids
            if event_id not in right_matched_event_ids
        ),
        right_only_matched_event_ids=tuple(
            event_id
            for event_id in right_matched_event_ids
            if event_id not in left_matched_event_ids
        ),
        warnings=warnings,
        deterministic_summary=_compare_summary(
            left=left,
            right=right,
            similarity=similarity,
            shared_primary_cycles=shared_primary_cycles,
            shared_matched_event_ids=shared_matched_event_ids,
        ),
    )


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _shared_cycle_labels(
    left_cycles: list[dict[str, object]],
    right_cycles: list[dict[str, object]],
) -> tuple[str, ...]:
    left_labels = {_cycle_label(cycle) for cycle in left_cycles}
    right_labels = {_cycle_label(cycle) for cycle in right_cycles}
    return tuple(sorted(left_labels & right_labels))


def _cycle_label(cycle: dict[str, object]) -> str:
    pair = cycle.get("pair", ())
    aspect = str(cycle.get("aspect", "unknown"))
    if isinstance(pair, list | tuple) and len(pair) == 2:
        return f"{pair[0]}-{pair[1]}:{aspect}"
    return f"unknown:{aspect}"


def _shared_event_ids(
    left_episodes: list[ResonanceEpisodeResponse],
    right_episodes: list[ResonanceEpisodeResponse],
    field_name: str,
) -> tuple[str, ...]:
    left_ids = set(_episode_event_ids(left_episodes, field_name))
    right_ids = set(_episode_event_ids(right_episodes, field_name))
    return tuple(sorted(left_ids & right_ids))


def _episode_event_ids(
    episodes: list[ResonanceEpisodeResponse],
    field_name: str,
) -> tuple[str, ...]:
    event_ids: list[str] = []
    for episode in episodes:
        events = getattr(episode, field_name)
        for event in events:
            if event.event_id not in event_ids:
                event_ids.append(event.event_id)
    return tuple(event_ids)


def _compare_warnings(
    left: ResonanceSearchResponse,
    right: ResonanceSearchResponse,
) -> tuple[str, ...]:
    warnings = [
        "This is a deterministic similarity comparison, not a prediction.",
        "AI must not add facts or events outside the backend response.",
    ]
    for label, search in (("left", left), ("right", right)):
        coverage_warning = search.index_coverage.warning
        if coverage_warning:
            warnings.append(f"{label}: {coverage_warning}")
    return tuple(warnings)


def _compare_summary(
    *,
    left: ResonanceSearchResponse,
    right: ResonanceSearchResponse,
    similarity: float,
    shared_primary_cycles: tuple[str, ...],
    shared_matched_event_ids: tuple[str, ...],
) -> str:
    cycle_text = ", ".join(shared_primary_cycles[:3]) if shared_primary_cycles else "brak"
    event_text = ", ".join(shared_matched_event_ids[:5]) if shared_matched_event_ids else "brak"
    return (
        f"Porownanie {left.query_datetime_utc} i {right.query_datetime_utc}: "
        f"podobienstwo wektorow zapytania {similarity:.3f}. "
        f"Wspolne glowne cykle: {cycle_text}. "
        f"Wspolne matched_events: {event_text}. "
        "To porownanie historyczno-symboliczne, nie prognoza."
    )


def _build_provider(provider_name: str) -> SyntheticEphemerisProvider | SwissEphemerisProvider:
    normalized = provider_name.strip().lower()
    if normalized == "synthetic":
        return SyntheticEphemerisProvider()
    if normalized == "swiss":
        try:
            return SwissEphemerisProvider()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider_name}")


def _load_or_build_index(
    *,
    request: ResonanceSearchRequest,
    provider: SyntheticEphemerisProvider | SwissEphemerisProvider,
    start_utc: datetime,
    end_utc: datetime,
    ephemeris_version: str,
    vector_index_root: Path | str,
) -> tuple[BuiltIndex, str, str | None, datetime, datetime]:
    if request.index_file is None:
        built_index = build_weekly_index(provider, start_utc, end_utc, step_days=request.step_days)
        return (
            built_index,
            "in_memory",
            None,
            built_index.rows[0].datetime_utc if built_index.rows else start_utc,
            built_index.rows[-1].datetime_utc if built_index.rows else end_utc,
        )
    index_path = _resolve_index_file(request.index_file, vector_index_root)
    try:
        built_index, metadata = load_built_index(index_path)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not load index file: {exc}") from exc
    _validate_index_metadata(
        built_index=built_index,
        metadata=metadata,
        request=request,
        start_utc=start_utc,
        end_utc=end_utc,
        ephemeris_version=ephemeris_version,
    )
    index_window_start = built_index.rows[0].datetime_utc
    index_window_end = built_index.rows[-1].datetime_utc
    built_index = _filter_index_to_window(
        built_index=built_index,
        start_utc=start_utc,
        end_utc=end_utc,
    )
    return built_index, "persistent_npz", request.index_file, index_window_start, index_window_end


def _resolve_index_file(index_file: str, vector_index_root: Path | str) -> Path:
    requested = Path(index_file)
    if requested.is_absolute() or requested.name != index_file or requested.suffix != ".npz":
        raise HTTPException(status_code=400, detail="index_file must be a local .npz filename.")
    path = Path(vector_index_root) / requested
    if not path.exists():
        raise HTTPException(status_code=404, detail="Index file was not found.")
    return path


def _validate_index_metadata(
    *,
    built_index: BuiltIndex,
    metadata: dict[str, object],
    request: ResonanceSearchRequest,
    start_utc: datetime,
    end_utc: datetime,
    ephemeris_version: str,
) -> None:
    expected = {
        "profile_id": request.profile_id,
        "vector_version": GLOBAL_SLOW_VECTOR_VERSION,
        "provider": ephemeris_version,
        "step_days": request.step_days,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise HTTPException(
                status_code=400,
                detail=f"Index metadata mismatch for {key}.",
            )
    if not built_index.rows:
        raise HTTPException(status_code=400, detail="Index file has no rows.")
    if built_index.matrix.shape[0] != len(built_index.rows):
        raise HTTPException(status_code=400, detail="Index matrix row count mismatch.")
    first = built_index.rows[0].datetime_utc
    last = built_index.rows[-1].datetime_utc
    required_start_utc = max(start_utc, RELIABLE_HISTORY_START_UTC)
    if first > required_start_utc:
        raise HTTPException(status_code=400, detail="Index does not cover request start.")
    if last + timedelta(days=request.step_days) <= end_utc:
        raise HTTPException(status_code=400, detail="Index does not cover request end.")


def _index_coverage_response(
    *,
    index_window_start: datetime,
    index_window_end: datetime,
    request_window_start: datetime,
    request_window_end: datetime,
) -> IndexCoverageResponse:
    status = _index_coverage_status(
        request_window_start=request_window_start,
        request_window_end=request_window_end,
    )
    return IndexCoverageResponse(
        reliable_history_start=RELIABLE_HISTORY_START_YEAR,
        reliable_history_end=RELIABLE_HISTORY_END_YEAR,
        index_window_start=index_window_start.isoformat(),
        index_window_end=index_window_end.isoformat(),
        request_window_start=request_window_start.isoformat(),
        request_window_end=request_window_end.isoformat(),
        index_coverage_status=status,
        history_window_label=_history_window_label(
            request_window_start=request_window_start,
            request_window_end=request_window_end,
        ),
        warning=_index_coverage_warning(status),
    )


def _index_coverage_status(
    *,
    request_window_start: datetime,
    request_window_end: datetime,
) -> str:
    if request_window_end.year < RELIABLE_HISTORY_START_YEAR:
        return "out_of_range"
    if (
        request_window_start.year < RELIABLE_HISTORY_START_YEAR
        or request_window_end.year > RELIABLE_HISTORY_END_YEAR
    ):
        return "partial"
    return "full"


def _history_window_label(
    *,
    request_window_start: datetime,
    request_window_end: datetime,
) -> str:
    if request_window_end.year < RELIABLE_HISTORY_START_YEAR:
        return "out_of_reliable_scope"
    if request_window_start.year < RELIABLE_MODERN_START_YEAR <= request_window_end.year:
        return "mixed_reliable"
    if request_window_start.year >= RELIABLE_MODERN_START_YEAR:
        return "reliable_modern"
    return "reliable_early_modern"


def _index_coverage_warning(status: str) -> str | None:
    if status == "partial":
        return "Request window only partially overlaps the reliable 1500-now history layer."
    if status == "out_of_range":
        return "Request window is outside the reliable 1500-now history layer."
    return None


def _filter_index_to_window(
    *,
    built_index: BuiltIndex,
    start_utc: datetime,
    end_utc: datetime,
) -> BuiltIndex:
    selected_positions = [
        position
        for position, row in enumerate(built_index.rows)
        if start_utc <= row.datetime_utc <= end_utc
    ]
    if not selected_positions:
        raise HTTPException(status_code=400, detail="Index has no rows inside request window.")
    return BuiltIndex(
        matrix=np.asarray(built_index.matrix[selected_positions, :], dtype=np.float64),
        rows=tuple(built_index.rows[position] for position in selected_positions),
    )


def _sky_state_response(dt_utc: datetime, provider_name: str) -> SkyStateResponse:
    provider = _build_provider(provider_name)
    state = provider.compute_state(dt_utc)
    return SkyStateResponse(
        provider=provider_name.strip().lower(),
        datetime_utc=state.datetime_utc.isoformat(),
        julian_day_ut=state.julian_day_ut,
        astro_profile_id=state.astro_profile_id,
        ephemeris_version=state.ephemeris_version,
        flags=state.flags,
        positions=[_planetary_position_response(position) for position in state.positions],
    )


def _planetary_position_response(position: PlanetaryPosition) -> PlanetaryPositionResponse:
    return PlanetaryPositionResponse(
        body=position.body,
        longitude_deg=position.longitude_deg,
        latitude_deg=position.latitude_deg,
        distance_au=position.distance_au,
        speed_longitude_deg_per_day=position.speed_longitude_deg_per_day,
        retrograde=position.retrograde,
    )


def _request_session_token(request: Request) -> str | None:
    header_token = request.headers.get(SESSION_TOKEN_HEADER)
    if header_token:
        return header_token
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _runtime_environment() -> str:
    return os.getenv(RUNTIME_ENV_ENV, "development").strip().lower() or "development"


def _is_production_environment(runtime_environment: str) -> bool:
    return runtime_environment == "production"


def _resolve_api_session_token(
    *,
    explicit_session_token: str | None,
    runtime_environment: str,
    require_auth: bool,
) -> str:
    env_session_token = os.getenv(SESSION_TOKEN_ENV, "").strip()
    resolved = explicit_session_token or env_session_token
    if resolved:
        return resolved
    if require_auth and _is_production_environment(runtime_environment):
        msg = f"{SESSION_TOKEN_ENV} is required when {RUNTIME_ENV_ENV}=production."
        raise RuntimeError(msg)
    return DEFAULT_DEV_SESSION_TOKEN


def _resolve_cors_allowed_origins(
    *,
    explicit_origins: tuple[str, ...] | None,
    runtime_environment: str,
) -> tuple[str, ...]:
    if explicit_origins is not None:
        return explicit_origins
    env_origins = _parse_cors_origins(os.getenv(CORS_ORIGINS_ENV, ""))
    if env_origins:
        return env_origins
    if _is_production_environment(runtime_environment):
        msg = f"{CORS_ORIGINS_ENV} is required when {RUNTIME_ENV_ENV}=production."
        raise RuntimeError(msg)
    return LOCAL_CORS_ORIGINS


def _parse_cors_origins(raw_origins: str) -> tuple[str, ...]:
    origins = tuple(
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    )
    if "*" in origins:
        msg = f"{CORS_ORIGINS_ENV} must not contain wildcard '*'."
        raise RuntimeError(msg)
    return origins


def _resolve_rate_limit_enabled(
    *,
    explicit_enabled: bool | None,
    runtime_environment: str,
) -> bool:
    if explicit_enabled is not None:
        return explicit_enabled
    env_enabled = os.getenv(RATE_LIMIT_ENABLED_ENV, "").strip().lower()
    if env_enabled in {"1", "true", "yes", "on"}:
        return True
    if env_enabled in {"0", "false", "no", "off"}:
        return False
    if env_enabled:
        msg = f"{RATE_LIMIT_ENABLED_ENV} must be true/false."
        raise RuntimeError(msg)
    return _is_production_environment(runtime_environment)


def _resolve_rate_limit_per_minute(*, explicit_limit: int | None) -> int:
    if explicit_limit is not None:
        limit = explicit_limit
    else:
        raw_limit = os.getenv(RATE_LIMIT_PER_MINUTE_ENV, "").strip()
        if not raw_limit:
            limit = DEFAULT_RATE_LIMIT_PER_MINUTE
        else:
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                msg = f"{RATE_LIMIT_PER_MINUTE_ENV} must be an integer."
                raise RuntimeError(msg) from exc
    if limit < 1:
        msg = f"{RATE_LIMIT_PER_MINUTE_ENV} must be >= 1."
        raise RuntimeError(msg)
    return limit


def _resolve_max_request_bytes(*, explicit_max_request_bytes: int | None) -> int:
    if explicit_max_request_bytes is not None:
        max_request_bytes = explicit_max_request_bytes
    else:
        raw_max_request_bytes = os.getenv(MAX_REQUEST_BYTES_ENV, "").strip()
        if not raw_max_request_bytes:
            max_request_bytes = DEFAULT_MAX_REQUEST_BYTES
        else:
            try:
                max_request_bytes = int(raw_max_request_bytes)
            except ValueError as exc:
                msg = f"{MAX_REQUEST_BYTES_ENV} must be an integer."
                raise RuntimeError(msg) from exc
    if max_request_bytes < 1:
        msg = f"{MAX_REQUEST_BYTES_ENV} must be >= 1."
        raise RuntimeError(msg)
    return max_request_bytes


def _request_size_limit_response(
    request: Request,
    *,
    max_request_bytes: int,
) -> JSONResponse | None:
    raw_content_length = request.headers.get("content-length")
    if raw_content_length is None:
        return None
    try:
        content_length = int(raw_content_length)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid Content-Length header."},
        )
    if content_length < 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid Content-Length header."},
        )
    if content_length <= max_request_bytes:
        return None
    return JSONResponse(
        status_code=413,
        content={
            "detail": "Astro Global API request body too large.",
            "max_request_bytes": max_request_bytes,
        },
    )


def _is_unmetered_path(path: str) -> bool:
    return path in {"/health", "/readiness"}


def _rate_limit_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    forwarded_client = forwarded_for.split(",", maxsplit=1)[0].strip()
    if forwarded_client:
        return forwarded_client
    if request.client and request.client.host:
        return request.client.host
    return "unknown-client"


def _today_snapshot_response(
    *,
    cache: dict[str, TodaySnapshotResponse],
    required_index_file: str,
    now_utc: datetime,
) -> TodaySnapshotResponse:
    today = now_utc.astimezone(UTC).date()
    cache_key = today.isoformat()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    generated_at = datetime(today.year, today.month, today.day, tzinfo=UTC)
    expires_at = generated_at + timedelta(days=1)
    snapshot = TodaySnapshotResponse(
        service="astro-global-core",
        snapshot_date_utc=cache_key,
        generated_at_utc=generated_at.isoformat(),
        expires_at_utc=expires_at.isoformat(),
        cache_key=f"today:{cache_key}:global_slow_v1",
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        provider="swiss",
        index_file=required_index_file,
        reliable_history_start=RELIABLE_HISTORY_START_YEAR,
        reliable_history_end=RELIABLE_HISTORY_END_YEAR,
        history_window_label="reliable_modern",
        recommended_search_request=ResonanceSearchRequest(
            date_utc=generated_at,
            profile_id=GLOBAL_SLOW_PROFILE_ID,
            lookback_years=120,
            lookahead_years=0,
            step_days=7,
            top_k=30,
            max_episodes=5,
            events_per_episode=6,
            event_window_years=1,
            provider="swiss",
            index_file=required_index_file,
        ),
        ui_contract=(
            "Use /today as a daily backend-authored snapshot seed.",
            "Run the recommended_search_request through POST /resonance/search.",
            "Render matched_events and context_events separately.",
            "Do not calculate planets, scoring, coverage, confidence or summaries in the UI.",
        ),
        warnings=(
            "This is not a prediction.",
            "AI is not a source of facts and must not add events outside backend data.",
            "Deep-history 1000-1500 is not part of the reliable core yet.",
        ),
    )
    cache.clear()
    cache[cache_key] = snapshot
    return snapshot


def _readiness_response(
    *,
    event_db_path: Path | str,
    vector_index_root: Path | str,
    required_index_file: str,
) -> ReadinessResponse:
    checks = [
        _swiss_readiness_check(),
        _event_store_readiness_check(event_db_path),
        _curated_data_readiness_check(),
        _index_readiness_check(
            vector_index_root=vector_index_root,
            required_index_file=required_index_file,
        ),
    ]
    status = "ready" if all(check.status == "ready" for check in checks) else "not_ready"
    return ReadinessResponse(
        service="astro-global-core",
        status=status,
        checked_at_utc=datetime.now(UTC).isoformat(),
        required_index_file=required_index_file,
        checks=checks,
    )


def _readiness_check(name: str, status: str, detail: str) -> ReadinessCheckResponse:
    return ReadinessCheckResponse(name=name, status=status, detail=detail)


def _swiss_readiness_check() -> ReadinessCheckResponse:
    if importlib.util.find_spec("swisseph") is None:
        return _readiness_check(
            "swiss_ephemeris",
            "not_ready",
            "Python module 'swisseph' is not installed.",
        )
    try:
        provider = SwissEphemerisProvider()
        probe = provider.compute_state(datetime(2026, 1, 1, tzinfo=UTC))
    except RuntimeError as exc:
        return _readiness_check("swiss_ephemeris", "not_ready", str(exc))
    return _readiness_check(
        "swiss_ephemeris",
        "ready",
        f"Swiss Ephemeris provider available: {probe.ephemeris_version}.",
    )


def _event_store_readiness_check(event_db_path: Path | str) -> ReadinessCheckResponse:
    path = Path(event_db_path)
    if not path.exists():
        return _readiness_check(
            "event_store",
            "not_ready",
            f"DuckDB event store not found: {path}.",
        )
    return _readiness_check("event_store", "ready", f"DuckDB event store found: {path}.")


def _curated_data_readiness_check() -> ReadinessCheckResponse:
    try:
        events = load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
        sources = event_sources_from_events(events)
    except ValueError as exc:
        return _readiness_check("curated_data", "not_ready", str(exc))

    missing_source_event_ids = sorted(
        {event.id for event in events} - {source.event_id for source in sources}
    )
    if missing_source_event_ids:
        return _readiness_check(
            "curated_data",
            "not_ready",
            f"Events without sources: {', '.join(missing_source_event_ids)}.",
        )
    return _readiness_check(
        "curated_data",
        "ready",
        f"Loaded {len(events)} curated events and {len(sources)} sources.",
    )


def _index_readiness_check(
    *,
    vector_index_root: Path | str,
    required_index_file: str,
) -> ReadinessCheckResponse:
    try:
        index_path = _resolve_index_file(required_index_file, vector_index_root)
        built_index, metadata = load_built_index(index_path)
    except HTTPException as exc:
        return _readiness_check("reliable_index", "not_ready", str(exc.detail))
    except (OSError, ValueError) as exc:
        return _readiness_check("reliable_index", "not_ready", str(exc))

    if not built_index.rows:
        return _readiness_check("reliable_index", "not_ready", "Index has no rows.")
    metadata_errors = _index_metadata_readiness_errors(metadata)
    if metadata_errors:
        return _readiness_check("reliable_index", "not_ready", "; ".join(metadata_errors))

    first = built_index.rows[0].datetime_utc
    last = built_index.rows[-1].datetime_utc
    if first > RELIABLE_HISTORY_START_UTC:
        return _readiness_check(
            "reliable_index",
            "not_ready",
            f"Index starts at {first.isoformat()}, after reliable start 1500-01-01.",
        )
    if last.year < RELIABLE_HISTORY_END_YEAR:
        return _readiness_check(
            "reliable_index",
            "not_ready",
            f"Index ends at {last.isoformat()}, before reliable end {RELIABLE_HISTORY_END_YEAR}.",
        )
    return _readiness_check(
        "reliable_index",
        "ready",
        (
            f"Index {required_index_file} covers {first.date().isoformat()}.."
            f"{last.date().isoformat()} with {len(built_index.rows)} rows."
        ),
    )


def _index_metadata_readiness_errors(metadata: dict[str, object]) -> list[str]:
    expected = {
        "profile_id": GLOBAL_SLOW_PROFILE_ID,
        "vector_version": GLOBAL_SLOW_VECTOR_VERSION,
        "step_days": 7,
    }
    errors = [
        f"{key}={metadata.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if metadata.get(key) != value
    ]
    if not str(metadata.get("provider", "")).strip():
        errors.append("provider metadata is missing")
    return errors


def _data_status_response(
    *,
    event_db_path: Path | str,
    auth_required: bool,
    cors_allowed_origins: tuple[str, ...],
    runtime_environment: str,
    rate_limit_enabled: bool,
    rate_limit_per_minute: int,
    max_request_bytes: int,
) -> DataStatusResponse:
    swiss_import_error = None
    swiss_available = importlib.util.find_spec("swisseph") is not None
    if not swiss_available:
        swiss_import_error = "Python module 'swisseph' is not installed."
    curated_events = load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
    curated_sources = load_curated_event_sources()
    sources_by_event: dict[str, list[object]] = defaultdict(list)
    for source in curated_sources:
        sources_by_event[source.event_id].append(source)
    events_without_sources = tuple(
        sorted(event.id for event in curated_events if not sources_by_event.get(event.id))
    )
    weak_precision_events_without_direct = tuple(
        sorted(
            event_id
            for event_id, sources in sources_by_event.items()
            if any(
                source.source_precision in {"contextual", "broad_context"}
                for source in sources
            )
            and not any(source.source_precision == "direct" for source in sources)
        )
    )
    ongoing_event_ids = tuple(sorted(event.id for event in curated_events if event.is_ongoing))
    duckdb_path = Path(event_db_path)
    return DataStatusResponse(
        service="astro-global-core",
        profiles=(GLOBAL_SLOW_PROFILE_ID,),
        vector_versions=("global_slow_v1.0",),
        providers=ProviderStatusResponse(
            default_provider="synthetic",
            synthetic_available=True,
            swiss_available=swiss_available,
            swiss_import_error=swiss_import_error,
        ),
        data_store=DataStoreStatusResponse(
            duckdb_path=str(duckdb_path),
            duckdb_exists=duckdb_path.exists(),
            curated_events_path=str(DEFAULT_CURATED_EVENTS_PATH),
            curated_events_count=len(curated_events),
            curated_event_sources_count=len(curated_sources),
            event_kind_counts=dict(Counter(event.event_kind for event in curated_events)),
            source_quality_counts=dict(
                Counter(source.source_quality for source in curated_sources)
            ),
            source_precision_counts=dict(
                Counter(source.source_precision for source in curated_sources)
            ),
            ongoing_events_count=len(ongoing_event_ids),
            ongoing_event_ids=ongoing_event_ids,
            events_without_curated_sources=events_without_sources,
            weak_precision_events_without_direct_backup=weak_precision_events_without_direct,
            fallback_to_curated_csv=True,
        ),
        security=ApiSecurityStatusResponse(
            runtime_environment=runtime_environment,
            auth_required=auth_required,
            token_header=SESSION_TOKEN_HEADER,
            cors_allowed_origins=cors_allowed_origins,
            rate_limit_enabled=rate_limit_enabled,
            rate_limit_per_minute=rate_limit_per_minute,
            max_request_bytes=max_request_bytes,
        ),
    )


def _episode_response(
    *,
    episode: object,
    event_db_path: Path | str,
    event_window_years: int,
    events_per_episode: int,
    index_rows: int,
    primary_cycles: list[dict[str, object]],
) -> ResonanceEpisodeResponse:
    events, omitted_point_events = find_event_selection_overlapping_years(
        start_astro_year=episode.period_start.year - event_window_years,
        end_astro_year=episode.period_end.year + event_window_years,
        db_path=event_db_path,
        limit=events_per_episode,
    )
    matched_events, context_events = _split_context_events(events)
    if context_events and len(matched_events) < events_per_episode:
        expanded_events, omitted_point_events = find_event_selection_overlapping_years(
            start_astro_year=episode.period_start.year - event_window_years,
            end_astro_year=episode.period_end.year + event_window_years,
            db_path=event_db_path,
            limit=events_per_episode + len(context_events),
        )
        expanded_matched_events, context_events = _split_context_events(expanded_events)
        matched_events = expanded_matched_events[:events_per_episode]
    response_event_ids = tuple(
        dict.fromkeys(
            [
                *(event.id for event in matched_events),
                *(event.id for event in context_events),
                *(event.id for event in omitted_point_events),
            ]
        )
    )
    sources_by_event = _sources_by_event(
        event_ids=response_event_ids,
        event_db_path=event_db_path,
    )
    coverage = build_coverage_report(matched_events)
    confidence = build_narrative_confidence(
        events=matched_events,
        sources_by_event=sources_by_event,
        coverage_warning=coverage.warning,
        requested_event_limit=events_per_episode,
    )
    strength = build_resonance_strength_breakdown(
        structural_similarity=episode.best_score,
        rarity_adjusted_percentile=episode.best_percentile,
        primary_cycles=primary_cycles,
        index_rows=index_rows,
    )
    return ResonanceEpisodeResponse(
        period_start=episode.period_start.isoformat(),
        period_end=episode.period_end.isoformat(),
        best_date=episode.best_date.isoformat(),
        best_score=episode.best_score,
        best_percentile=episode.best_percentile,
        row_indices=episode.row_indices,
        matched_events=[
            _historical_event_response(event=event, sources=sources_by_event.get(event.id, []))
            for event in matched_events
        ],
        context_events=[
            _historical_event_response(event=event, sources=sources_by_event.get(event.id, []))
            for event in context_events
        ],
        omitted_point_events=[
            _historical_event_response(event=event, sources=sources_by_event.get(event.id, []))
            for event in omitted_point_events
        ],
        event_coverage=EventCoverageResponse(**coverage.model_dump()),
        score_breakdown=ScoreBreakdownResponse(
            structural_similarity=strength.structural_similarity,
            cycle_power_score=strength.cycle_power_score,
            rarity_adjusted_percentile=strength.rarity_adjusted_percentile,
            planetary_resonance_score=strength.planetary_resonance_score,
            label=strength.label,
            primary_cycle_count=strength.primary_cycle_count,
            strongest_primary_contribution=strength.strongest_primary_contribution,
            rare_configuration=strength.rare_configuration,
            insufficient_comparable_history=strength.insufficient_comparable_history,
        ),
        narrative_confidence=NarrativeConfidenceResponse(
            event_coverage_score=confidence.event_coverage_score,
            source_quality_score=confidence.source_quality_score,
            evidence_confidence=confidence.evidence_confidence,
            narrative_confidence=confidence.narrative_confidence,
        ),
    )


def _split_context_events(
    events: tuple[object, ...],
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    matched_events: list[object] = []
    context_events: list[object] = []
    for event in events:
        event_id = str(getattr(event, "id", ""))
        if is_broad_context_event_id(event_id):
            context_events.append(event)
        else:
            matched_events.append(event)
    return tuple(matched_events), tuple(context_events)


def _sources_by_event(
    *,
    event_ids: tuple[str, ...],
    event_db_path: Path | str,
) -> dict[str, list[EventSourceResponse]]:
    sources_by_event: dict[str, list[EventSourceResponse]] = {
        event_id: [] for event_id in event_ids
    }
    for source in find_sources_for_event_ids(event_ids=event_ids, db_path=event_db_path):
        sources_by_event.setdefault(source.event_id, []).append(
            EventSourceResponse(
                source_id=source.id,
                source_type=source.source_type,
                source_name=source.source_name,
                source_url=str(source.source_url),
                source_quality=source.source_quality,
                source_precision=source.source_precision,
            )
        )
    return sources_by_event


def _historical_event_response(
    *,
    event: object,
    sources: list[EventSourceResponse],
) -> HistoricalEventResponse:
    return HistoricalEventResponse(
        event_id=event.id,
        title=event.title,
        display_date=event.display_date,
        start_astro_year=event.start_astro_year,
        end_astro_year=event.end_astro_year,
        category=event.category,
        event_kind=event.event_kind,
        is_ongoing=event.is_ongoing,
        end_year_policy=event.end_year_policy,
        region=event.region,
        geo_scope=event.geo_scope,
        source_url=str(event.source_url),
        confidence_score=event.confidence_score,
        sources=sources,
    )


app = create_app()
