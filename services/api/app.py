from __future__ import annotations

import importlib.util
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.api.product_catalog import (
    article_seeds_response,
    resonance_compare_presets_response,
    timeline_seeds_response,
)
from services.api.schemas import (
    MAX_EVENTS_WINDOW,
    ActiveCycleWindowResponse,
    ActiveRegimeWindowResponse,
    ApiSecurityStatusResponse,
    ArticleSeedsResponse,
    DataStatusResponse,
    DataStoreStatusResponse,
    EventCoverageResponse,
    EventSourceResponse,
    EventsWindowResponse,
    HistoricalAnaloguePolicyResponse,
    HistoricalEventResponse,
    IndexCoverageResponse,
    NarrativeConfidenceResponse,
    PlanetaryPositionResponse,
    ProviderStatusResponse,
    ReadinessCheckResponse,
    ReadinessResponse,
    RelatedResonanceWindowResponse,
    ResonanceBasisDriverResponse,
    ResonanceBasisResponse,
    ResonanceComparePresetsResponse,
    ResonanceCompareRequest,
    ResonanceCompareResponse,
    ResonanceEpisodeResponse,
    ResonanceSearchRequest,
    ResonanceSearchResponse,
    ScoreBreakdownResponse,
    SkyAtDateRequest,
    SkyStateResponse,
    TimelineSeedsResponse,
    TodaySnapshotResponse,
)
from services.astro_rules.signs import placement_for_longitude
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
    POINT_EVENT_KINDS,
    find_event_selection_overlapping_years,
    find_events_overlapping_years,
    find_sources_for_event_ids,
)
from services.narrative.confidence import build_narrative_confidence
from services.narrative.deterministic_summary import build_deterministic_summary
from services.resonance.episode_clustering import (
    CandidatePoint,
    EpisodeEventProfile,
    ResonanceEpisode,
    SuppressedNearbyMatch,
    cluster_candidate_points,
    select_diverse_episodes,
)
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import BuiltIndex, build_weekly_index
from services.resonance.index_store import load_built_index
from services.resonance.scoring import (
    build_resonance_strength_breakdown,
    calibrate_structural_similarity,
    outer_sign_environment_similarity,
    shared_outer_aspect_similarity,
)
from services.resonance.vectorizer import (
    GLOBAL_SLOW_PROFILE_ID,
    GLOBAL_SLOW_VECTOR_VERSION,
    vectorize_global_slow,
)

DEFAULT_VECTOR_INDEX_ROOT = Path("data/vectors")
SESSION_TOKEN_HEADER = "x-astro-global-session"
SESSION_TOKEN_ENV = "ASTRO_GLOBAL_SESSION_TOKEN"
RUNTIME_ENV_ENV = "ASTRO_GLOBAL_ENV"
CORS_ORIGINS_ENV = "ASTRO_GLOBAL_CORS_ORIGINS"
RATE_LIMIT_ENABLED_ENV = "ASTRO_GLOBAL_RATE_LIMIT_ENABLED"
RATE_LIMIT_PER_MINUTE_ENV = "ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE"
MAX_REQUEST_BYTES_ENV = "ASTRO_GLOBAL_MAX_REQUEST_BYTES"


@dataclass(frozen=True)
class EventTemporalMatch:
    precision: str
    relation: str
    score: float
    start: date | None = None
    end: date | None = None


EXACT_WINDOW_EVENT_PRECISIONS = frozenset(
    {"exact_date", "exact_date_range", "month_range"}
)
EXACT_WINDOW_EVENT_RELATIONS = frozenset(
    {"exact_date_in_window", "exact_range_overlaps_window"}
)
MAX_PEAK_CONTEXT_DURATION_DAYS = 50 * 366
LOW_VALUE_REGIONAL_WAR_MAX_YEARS = 5
DEFAULT_DEV_SESSION_TOKEN = "dev-local-token"
DEFAULT_REQUIRED_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_MAX_REQUEST_BYTES = 65536
REGIME_SIGN_BODIES = ("Uranus", "Neptune", "Pluto")
REGIME_SIGN_SCAN_STEP_DAYS = 31
REGIME_CYCLE_SCAN_STEP_DAYS = 7
REGIME_MAX_SIGN_SCAN_YEARS = {
    "Uranus": 9,
    "Neptune": 16,
    "Pluto": 30,
}
REGIME_MAX_CYCLE_SCAN_YEARS = 8
RELIABLE_HISTORY_START_YEAR = 1500
RELIABLE_MODERN_START_YEAR = 1900
RELIABLE_HISTORY_END_YEAR = 2026
RELIABLE_HISTORY_START_UTC = datetime(RELIABLE_HISTORY_START_YEAR, 1, 1, tzinfo=UTC)
LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


@dataclass(frozen=True)
class ActiveRegimeWindow:
    driver_id: str
    driver_type: str
    label: str
    start_date: date
    end_date: date
    source: str


@dataclass(frozen=True)
class ActiveCycleWindow:
    cycle_id: str
    planets: tuple[str, ...]
    aspect: str
    role: str
    label: str
    start_date: date
    peak_date: date | None
    end_date: date
    orb_at_query: float | None
    closeness_at_query: float | None
    confidence_scope: str


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

    @app.get("/resonance/compare/presets", response_model=ResonanceComparePresetsResponse)
    def resonance_compare_presets() -> ResonanceComparePresetsResponse:
        return resonance_compare_presets_response(required_index_file=required_index_file)

    @app.get("/articles/seeds", response_model=ArticleSeedsResponse)
    def article_seeds() -> ArticleSeedsResponse:
        return article_seeds_response(required_index_file=required_index_file)

    @app.get("/timeline/seeds", response_model=TimelineSeedsResponse)
    def timeline_seeds() -> TimelineSeedsResponse:
        return timeline_seeds_response(required_index_file=required_index_file)

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
        index_step_days=request.step_days,
        request_window_start=start_utc,
        request_window_end=end_utc,
    )
    search_top_k = len(built_index.rows) if request.historical_analogue_mode else request.top_k
    hits = exact_search(built_index.matrix, query_vector.vector, top_k=search_top_k)
    points = _candidate_points_from_hits(
        hits=hits,
        built_index=built_index,
        query_vector=query_vector.vector,
    )
    primary_cycles = query_vector.cycle_strength_debug_json["primary_cycles"]
    supporting_cycles = query_vector.cycle_strength_debug_json["supporting_cycles"]
    active_cycle_windows = _active_cycle_windows(
        provider=provider,
        query_dt=query_dt,
        primary_cycles=primary_cycles,
        supporting_cycles=supporting_cycles,
        enabled=request.historical_analogue_mode
        and request.historical_exclude_active_regime_windows,
    )
    active_regime_windows = _active_regime_windows(
        provider=provider,
        query_dt=query_dt,
        query_state=query_state,
        cycle_windows=active_cycle_windows,
        enabled=request.historical_analogue_mode
        and request.historical_exclude_active_regime_windows,
    )
    local_points, historical_points = _split_local_and_historical_points(
        points=points,
        query_dt=query_dt,
        request=request,
        active_regime_windows=active_regime_windows,
    )
    local_episodes = cluster_candidate_points(local_points[: request.top_k])[
        : request.max_episodes
    ]
    raw_historical_episodes = _historical_candidate_episodes_from_points(
        points=historical_points,
        request=request,
    )
    event_profiles = _event_profiles_for_episodes(
        episodes=raw_historical_episodes,
        provider=provider,
        event_db_path=event_db_path,
        event_window_years=request.event_window_years,
        events_per_episode=request.events_per_episode,
    )
    diverse_episodes = select_diverse_episodes(
        raw_historical_episodes,
        max_episodes=request.max_episodes,
        event_profiles=event_profiles,
        default_min_year_gap=5,
        pre_1900_event_min_year_gap=10,
    )

    episode_responses = [
        _episode_response(
            episode=selected_episode.episode,
            provider=provider,
            query_state=query_state,
            event_db_path=event_db_path,
            event_window_years=request.event_window_years,
            events_per_episode=request.events_per_episode,
            index_rows=len(built_index.rows),
            primary_cycles=primary_cycles,
            related_windows=selected_episode.related_windows,
        )
        for selected_episode in diverse_episodes
    ]
    local_episode_responses = [
        _episode_response(
            episode=episode,
            provider=provider,
            query_state=query_state,
            event_db_path=event_db_path,
            event_window_years=request.event_window_years,
            events_per_episode=request.events_per_episode,
            index_rows=len(built_index.rows),
            primary_cycles=primary_cycles,
        )
        for episode in local_episodes
    ]
    local_resonance_response = (
        local_episode_responses[0] if local_episode_responses else None
    )

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
        historical_analogues=episode_responses,
        raw_historical_candidates=[
            _related_window_response(
                episode=episode,
                reason="raw_candidate",
                event_overlap=0.0,
            )
            for episode in raw_historical_episodes
        ],
        local_resonance=local_resonance_response,
        nearby_matches=local_episode_responses,
        local_resonance_window=local_episode_responses,
        active_regime_windows=[
            _active_regime_window_response(window) for window in active_regime_windows
        ],
        active_background_cycles=[
            _active_regime_window_response(window) for window in active_regime_windows
        ],
        active_cycle_windows=[
            _active_cycle_window_response(window) for window in active_cycle_windows
        ],
        regime_cycle_windows=[
            _active_cycle_window_response(window) for window in active_cycle_windows
        ],
        analogue_policy=HistoricalAnaloguePolicyResponse(
            historical_analogue_mode=request.historical_analogue_mode,
            exclude_same_calendar_year=request.exclude_same_calendar_year,
            local_resonance_window_days=request.local_resonance_window_days,
            historical_analogue_min_year_gap=request.historical_analogue_min_year_gap,
            historical_exclude_active_regime_windows=(
                request.historical_exclude_active_regime_windows
            ),
            local_resonance_excluded=request.historical_analogue_mode
            and local_resonance_response is not None,
            excluded_local_episodes_count=len(local_episodes)
            if request.historical_analogue_mode
            else 0,
        ),
        deterministic_summary=build_deterministic_summary(
            profile_id=query_vector.profile_id,
            query_datetime_utc=query_state.datetime_utc.isoformat(),
            primary_cycles=primary_cycles,
            supporting_cycles=supporting_cycles,
            episodes=episode_responses,
        ),
    )


def _candidate_points_from_hits(
    *,
    hits: list[object],
    built_index: BuiltIndex,
    query_vector: np.ndarray,
) -> list[CandidatePoint]:
    points: list[CandidatePoint] = []
    for hit in hits:
        row = built_index.rows[hit.row_index]
        candidate_vector = built_index.matrix[hit.row_index]
        score = calibrate_structural_similarity(
            raw_score=hit.score,
            query_vector=query_vector,
            candidate_vector=candidate_vector,
        )
        points.append(
            CandidatePoint(
                date=row.datetime_utc.date(),
                score=score,
                row_index=row.row_index,
                percentile=hit.percentile,
            )
        )
    points.sort(key=lambda point: point.score, reverse=True)
    return points


def _historical_candidate_pool_limit(
    *,
    request: ResonanceSearchRequest,
    available_count: int,
) -> int:
    if not request.historical_analogue_mode:
        return min(request.top_k, available_count)
    deeper_pool = max(request.top_k, request.max_episodes * 500, 1500)
    return min(deeper_pool, available_count)


def _historical_episodes_from_points(
    *,
    points: list[CandidatePoint],
    request: ResonanceSearchRequest,
):
    return _historical_candidate_episodes_from_points(
        points=points,
        request=request,
    )[: request.max_episodes]


def _historical_candidate_episodes_from_points(
    *,
    points: list[CandidatePoint],
    request: ResonanceSearchRequest,
) -> list[ResonanceEpisode]:
    if not request.historical_analogue_mode:
        return cluster_candidate_points(points[: request.top_k])

    primary_episodes = cluster_candidate_points(points[: request.top_k])
    deeper_limit = _historical_candidate_pool_limit(
        request=request,
        available_count=len(points),
    )
    deeper_episodes = cluster_candidate_points(points[:deeper_limit])
    combined = list(primary_episodes)
    for episode in deeper_episodes:
        if any(
            abs((episode.best_date - existing.best_date).days) < 365
            for existing in combined
        ):
            continue
        combined.append(episode)
    return combined


def _event_profiles_for_episodes(
    *,
    episodes: list[ResonanceEpisode],
    provider: object,
    event_db_path: Path | str,
    event_window_years: int,
    events_per_episode: int,
) -> dict[ResonanceEpisode, EpisodeEventProfile]:
    return {
        episode: _event_profile_for_episode(
            episode=episode,
            provider=provider,
            event_db_path=event_db_path,
            event_window_years=event_window_years,
            events_per_episode=events_per_episode,
        )
        for episode in episodes
    }


def _event_profile_for_episode(
    *,
    episode: ResonanceEpisode,
    provider: object,
    event_db_path: Path | str,
    event_window_years: int,
    events_per_episode: int,
) -> EpisodeEventProfile:
    candidate_limit = max(events_per_episode * 6, events_per_episode, 20)
    events, _omitted_point_events = find_event_selection_overlapping_years(
        start_astro_year=episode.period_start.year - event_window_years,
        end_astro_year=episode.period_end.year + event_window_years,
        db_path=event_db_path,
        limit=candidate_limit,
    )
    matched_events, context_events, _temporal_matches = _classify_events_for_episode_window(
        events=events,
        window_start=_as_date(episode.period_start),
        window_end=_as_date(episode.period_end),
        limit=events_per_episode,
    )
    profile_events = (*matched_events, *context_events)
    return EpisodeEventProfile(
        event_ids=frozenset(str(getattr(event, "id", "")) for event in profile_events),
        long_process_event_ids=frozenset(
            str(getattr(event, "id", ""))
            for event in profile_events
            if str(getattr(event, "event_kind", "")) not in POINT_EVENT_KINDS
            or bool(getattr(event, "is_ongoing", False))
            or is_broad_context_event_id(str(getattr(event, "id", "")))
        ),
        driver_keys=_resonance_driver_keys_for_date(
            provider=provider,
            target_date=episode.best_date,
        ),
    )


def _resonance_driver_keys_for_date(
    *,
    provider: object,
    target_date: date,
) -> frozenset[str]:
    state = provider.compute_state(_as_datetime_utc(target_date))
    return frozenset(
        f"{driver.driver_type}:{_basis_driver_key(driver)[1]}"
        for driver in _basis_drivers_for_state(state)
    )


def _active_regime_window_response(
    window: ActiveRegimeWindow,
) -> ActiveRegimeWindowResponse:
    return ActiveRegimeWindowResponse(
        driver_id=window.driver_id,
        driver_type=window.driver_type,
        label=window.label,
        start_date=window.start_date.isoformat(),
        end_date=window.end_date.isoformat(),
        source=window.source,
    )


def _active_cycle_window_response(
    window: ActiveCycleWindow,
) -> ActiveCycleWindowResponse:
    return ActiveCycleWindowResponse(
        cycle_id=window.cycle_id,
        planets=window.planets,
        aspect=window.aspect,
        role=window.role,
        label=window.label,
        start_date=window.start_date.isoformat(),
        peak_date=window.peak_date.isoformat() if window.peak_date is not None else None,
        end_date=window.end_date.isoformat(),
        orb_at_query=window.orb_at_query,
        closeness_at_query=window.closeness_at_query,
        confidence_scope=window.confidence_scope,
    )


def _active_cycle_windows(
    *,
    provider: object,
    query_dt: datetime,
    primary_cycles: list[dict[str, object]],
    supporting_cycles: list[dict[str, object]],
    enabled: bool,
) -> list[ActiveCycleWindow]:
    if not enabled:
        return []
    return [
        _scan_active_cycle_window(
            provider=provider,
            query_dt=query_dt,
            cycle=cycle,
        )
        for cycle in _active_cycle_regime_drivers(primary_cycles, supporting_cycles)
    ]


def _active_regime_windows(
    *,
    provider: object,
    query_dt: datetime,
    query_state: object,
    cycle_windows: list[ActiveCycleWindow],
    enabled: bool,
) -> list[ActiveRegimeWindow]:
    if not enabled:
        return []
    windows = [
        ActiveRegimeWindow(
            driver_id=f"cycle:{window.cycle_id}",
            driver_type="cycle",
            label=window.label,
            start_date=window.start_date,
            end_date=window.end_date,
            source="query_active_cycle",
        )
        for window in cycle_windows
    ]
    for body in REGIME_SIGN_BODIES:
        windows.append(
            _scan_sign_regime_window(
                provider=provider,
                query_dt=query_dt,
                query_state=query_state,
                body=body,
            )
        )
    return _dedupe_active_regime_windows(windows)


def _active_cycle_regime_drivers(
    primary_cycles: list[dict[str, object]],
    supporting_cycles: list[dict[str, object]],
) -> list[dict[str, object]]:
    cycles = list(primary_cycles) + list(supporting_cycles)
    return sorted(
        cycles,
        key=lambda item: (
            str(item.get("role", "")) != "primary",
            -float(item.get("contribution", 0.0)),
        ),
    )


def _scan_active_cycle_window(
    *,
    provider: object,
    query_dt: datetime,
    cycle: dict[str, object],
) -> ActiveCycleWindow:
    pair = tuple(str(item) for item in cycle.get("pair", ()))
    aspect = str(cycle.get("aspect", ""))
    cycle_id = f"{'-'.join(pair)}:{aspect}"
    label = f"{'-'.join(pair)} {aspect}".strip()
    start_date = _scan_cycle_regime_boundary(
        provider=provider,
        query_dt=query_dt,
        cycle=cycle,
        direction=-1,
    )
    end_date = _scan_cycle_regime_boundary(
        provider=provider,
        query_dt=query_dt,
        cycle=cycle,
        direction=1,
    )
    peak_date = _sample_cycle_peak_date(
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        cycle=cycle,
    )
    return ActiveCycleWindow(
        cycle_id=cycle_id,
        planets=pair,
        aspect=aspect,
        role=str(cycle.get("role", "supporting")),
        label=label,
        start_date=start_date,
        peak_date=peak_date,
        end_date=end_date,
        orb_at_query=(
            float(cycle["orb_deg"]) if isinstance(cycle.get("orb_deg"), (int, float)) else None
        ),
        closeness_at_query=(
            float(cycle["closeness"])
            if isinstance(cycle.get("closeness"), (int, float))
            else None
        ),
        confidence_scope="sampled_weekly_from_ephemeris",
    )


def _sample_cycle_peak_date(
    *,
    provider: object,
    start_date: date,
    end_date: date,
    cycle: dict[str, object],
) -> date | None:
    best_date: date | None = None
    best_orb: float | None = None
    current = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC)
    while current <= end_dt:
        state = provider.compute_state(current)
        vector = vectorize_global_slow(state)
        active_cycles = (
            vector.cycle_strength_debug_json["primary_cycles"]
            + vector.cycle_strength_debug_json["supporting_cycles"]
        )
        matching_cycle = next(
            (
                active_cycle
                for active_cycle in active_cycles
                if _same_cycle_driver(active_cycle, cycle)
            ),
            None,
        )
        if matching_cycle is not None:
            orb = float(matching_cycle.get("orb_deg", 999.0))
            if best_orb is None or orb < best_orb:
                best_orb = orb
                best_date = current.date()
        current += timedelta(days=REGIME_CYCLE_SCAN_STEP_DAYS)
    return best_date


def _scan_cycle_regime_boundary(
    *,
    provider: object,
    query_dt: datetime,
    cycle: dict[str, object],
    direction: int,
) -> date:
    boundary = query_dt.date()
    max_steps = int((REGIME_MAX_CYCLE_SCAN_YEARS * 365) / REGIME_CYCLE_SCAN_STEP_DAYS)
    for step in range(1, max_steps + 1):
        candidate_dt = query_dt + timedelta(
            days=direction * step * REGIME_CYCLE_SCAN_STEP_DAYS
        )
        state = provider.compute_state(candidate_dt)
        vector = vectorize_global_slow(state)
        active_cycles = (
            vector.cycle_strength_debug_json["primary_cycles"]
            + vector.cycle_strength_debug_json["supporting_cycles"]
        )
        if not any(_same_cycle_driver(active_cycle, cycle) for active_cycle in active_cycles):
            break
        boundary = candidate_dt.date()
    return boundary


def _scan_sign_regime_window(
    *,
    provider: object,
    query_dt: datetime,
    query_state: object,
    body: str,
) -> ActiveRegimeWindow:
    position = query_state.position_by_body(body)
    placement = placement_for_longitude(position.longitude_deg)
    sign_label = placement.sign
    start_date = _scan_sign_regime_boundary(
        provider=provider,
        query_dt=query_dt,
        body=body,
        sign_index=placement.sign_index,
        direction=-1,
    )
    end_date = _scan_sign_regime_boundary(
        provider=provider,
        query_dt=query_dt,
        body=body,
        sign_index=placement.sign_index,
        direction=1,
    )
    return ActiveRegimeWindow(
        driver_id=f"sign:{body}:{sign_label}",
        driver_type="sign_regime",
        label=f"{body} in {sign_label}",
        start_date=start_date,
        end_date=end_date,
        source="query_slow_body_sign",
    )


def _scan_sign_regime_boundary(
    *,
    provider: object,
    query_dt: datetime,
    body: str,
    sign_index: int,
    direction: int,
) -> date:
    boundary = query_dt.date()
    max_years = REGIME_MAX_SIGN_SCAN_YEARS[body]
    max_steps = int((max_years * 365) / REGIME_SIGN_SCAN_STEP_DAYS)
    for step in range(1, max_steps + 1):
        candidate_dt = query_dt + timedelta(
            days=direction * step * REGIME_SIGN_SCAN_STEP_DAYS
        )
        state = provider.compute_state(candidate_dt)
        placement = placement_for_longitude(state.position_by_body(body).longitude_deg)
        if placement.sign_index != sign_index:
            break
        boundary = candidate_dt.date()
    return boundary


def _same_cycle_driver(
    candidate: dict[str, object],
    query_cycle: dict[str, object],
) -> bool:
    return tuple(candidate.get("pair", ())) == tuple(query_cycle.get("pair", ())) and str(
        candidate.get("aspect", "")
    ) == str(query_cycle.get("aspect", ""))


def _dedupe_active_regime_windows(
    windows: list[ActiveRegimeWindow],
) -> list[ActiveRegimeWindow]:
    deduped: dict[str, ActiveRegimeWindow] = {}
    for window in windows:
        existing = deduped.get(window.driver_id)
        if existing is None:
            deduped[window.driver_id] = window
            continue
        deduped[window.driver_id] = ActiveRegimeWindow(
            driver_id=window.driver_id,
            driver_type=window.driver_type,
            label=window.label,
            start_date=min(existing.start_date, window.start_date),
            end_date=max(existing.end_date, window.end_date),
            source=window.source,
        )
    return sorted(deduped.values(), key=lambda item: (item.start_date, item.driver_id))


def _split_local_and_historical_points(
    *,
    points: list[CandidatePoint],
    query_dt: datetime,
    request: ResonanceSearchRequest,
    active_regime_windows: list[ActiveRegimeWindow] | None = None,
) -> tuple[list[CandidatePoint], list[CandidatePoint]]:
    if not request.historical_analogue_mode:
        return [], points

    local_points: list[CandidatePoint] = []
    historical_points: list[CandidatePoint] = []
    query_date = query_dt.date()
    for point in points:
        if _is_local_resonance_date(
            candidate_date=point.date,
            query_date=query_date,
            exclude_same_calendar_year=request.exclude_same_calendar_year,
            local_resonance_window_days=request.local_resonance_window_days,
            min_year_gap=request.historical_analogue_min_year_gap,
            active_regime_windows=active_regime_windows or [],
        ):
            local_points.append(point)
        else:
            historical_points.append(point)
    return local_points, historical_points


def _is_local_resonance_date(
    *,
    candidate_date: date,
    query_date: date,
    exclude_same_calendar_year: bool,
    local_resonance_window_days: int,
    min_year_gap: int,
    active_regime_windows: list[ActiveRegimeWindow],
) -> bool:
    if any(
        window.start_date <= candidate_date <= window.end_date
        for window in active_regime_windows
    ):
        return True
    if exclude_same_calendar_year and candidate_date.year == query_date.year:
        return True
    if abs((candidate_date - query_date).days) <= local_resonance_window_days:
        return True
    return abs(candidate_date.year - query_date.year) < min_year_gap


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
    if not request.historical_analogue_mode:
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
    required_start_utc = max(start_utc, RELIABLE_HISTORY_START_UTC)
    if first > required_start_utc:
        raise HTTPException(status_code=400, detail="Index does not cover request start.")


def _index_coverage_response(
    *,
    index_window_start: datetime,
    index_window_end: datetime,
    index_step_days: int,
    request_window_start: datetime,
    request_window_end: datetime,
) -> IndexCoverageResponse:
    status = _index_coverage_status(
        index_window_start=index_window_start,
        index_window_end=index_window_end,
        index_step_days=index_step_days,
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
    index_window_start: datetime,
    index_window_end: datetime,
    index_step_days: int,
    request_window_start: datetime,
    request_window_end: datetime,
) -> str:
    if request_window_end.year < RELIABLE_HISTORY_START_YEAR:
        return "out_of_range"
    if (
        request_window_start.year < RELIABLE_HISTORY_START_YEAR
        or request_window_end.year > RELIABLE_HISTORY_END_YEAR
        or index_window_start > max(request_window_start, RELIABLE_HISTORY_START_UTC)
        or index_window_end + timedelta(days=index_step_days) <= request_window_end
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
    provider: object,
    query_state: object,
    event_db_path: Path | str,
    event_window_years: int,
    events_per_episode: int,
    index_rows: int,
    primary_cycles: list[dict[str, object]],
    related_windows: tuple[SuppressedNearbyMatch, ...] = (),
) -> ResonanceEpisodeResponse:
    candidate_limit = max(events_per_episode * 6, events_per_episode, 20)
    context_related_windows = _context_related_windows(related_windows)
    event_fetch_start = min(
        [
            episode.period_start,
            *(related.episode.period_start for related in context_related_windows),
        ]
    )
    event_fetch_end = max(
        [
            episode.period_end,
            *(related.episode.period_end for related in context_related_windows),
        ]
    )
    events, omitted_point_events = find_event_selection_overlapping_years(
        start_astro_year=event_fetch_start.year - event_window_years,
        end_astro_year=event_fetch_end.year + event_window_years,
        db_path=event_db_path,
        limit=candidate_limit,
    )
    matched_events, context_events, temporal_matches = _classify_events_for_episode_window(
        events=events,
        window_start=_as_date(episode.period_start),
        window_end=_as_date(episode.period_end),
        limit=events_per_episode,
    )
    if context_related_windows:
        context_events, temporal_matches = _cluster_context_events_for_related_windows(
            events=events,
            episode=episode,
            related_windows=context_related_windows,
            matched_events=matched_events,
            peak_temporal_matches=temporal_matches,
            limit=events_per_episode,
        )
    selected_context_ids = {event.id for event in context_events}
    omitted_point_events = tuple(
        event for event in omitted_point_events if event.id not in selected_context_ids
    )
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
    query_vector = vectorize_global_slow(query_state).vector
    historical_state = provider.compute_state(_as_datetime_utc(episode.best_date))
    historical_vector = vectorize_global_slow(historical_state).vector
    return ResonanceEpisodeResponse(
        period_start=episode.period_start.isoformat(),
        period_end=episode.period_end.isoformat(),
        best_date=episode.best_date.isoformat(),
        best_score=episode.best_score,
        best_percentile=episode.best_percentile,
        row_indices=episode.row_indices,
        matched_events=[
            _historical_event_response(
                event=event,
                sources=sources_by_event.get(event.id, []),
                temporal_match=temporal_matches.get(event.id),
            )
            for event in matched_events
        ],
        context_events=[
            _historical_event_response(
                event=event,
                sources=sources_by_event.get(event.id, []),
                temporal_match=temporal_matches.get(event.id),
            )
            for event in context_events
        ],
        omitted_point_events=[
            _historical_event_response(
                event=event,
                sources=sources_by_event.get(event.id, []),
                temporal_match=temporal_matches.get(event.id),
            )
            for event in omitted_point_events
        ],
        event_coverage=EventCoverageResponse(**coverage.model_dump()),
        score_breakdown=ScoreBreakdownResponse(
            structural_similarity=strength.structural_similarity,
            cycle_power_score=strength.cycle_power_score,
            rarity_adjusted_percentile=strength.rarity_adjusted_percentile,
            planetary_resonance_score=strength.planetary_resonance_score,
            outer_sign_environment_similarity=outer_sign_environment_similarity(
                query_vector,
                historical_vector,
            ),
            shared_outer_aspect_similarity=shared_outer_aspect_similarity(
                query_vector,
                historical_vector,
            ),
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
        resonance_basis=_resonance_basis_response(
            provider=provider,
            query_state=query_state,
            historical_dt=_as_datetime_utc(episode.best_date),
        ),
        related_windows=[
            _related_window_response(
                episode=related.episode,
                reason=related.reason,
                event_overlap=related.event_overlap,
            )
            for related in related_windows
        ],
    )


def _related_window_response(
    *,
    episode: ResonanceEpisode,
    reason: str,
    event_overlap: float,
) -> RelatedResonanceWindowResponse:
    return RelatedResonanceWindowResponse(
        period_start=episode.period_start.isoformat(),
        period_end=episode.period_end.isoformat(),
        best_date=episode.best_date.isoformat(),
        best_score=episode.best_score,
        best_percentile=episode.best_percentile,
        row_indices=episode.row_indices,
        reason=reason,
        event_overlap=round(event_overlap, 4),
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


def _classify_events_for_episode_window(
    *,
    events: tuple[object, ...],
    window_start: date,
    window_end: date,
    limit: int,
) -> tuple[tuple[object, ...], tuple[object, ...], dict[str, EventTemporalMatch]]:
    temporal_matches = {
        str(getattr(event, "id", "")): _event_temporal_match(
            event=event,
            window_start=window_start,
            window_end=window_end,
        )
        for event in events
    }
    matched_events = tuple(
        event
        for event in events
        if _is_exact_window_event(
            event=event,
            temporal_match=temporal_matches[str(getattr(event, "id", ""))],
        )
    )
    context_events = tuple(
        event
        for event in events
        if event not in matched_events
        and _is_context_event(
            event=event,
            temporal_match=temporal_matches[str(getattr(event, "id", ""))],
        )
    )
    return (
        _sort_temporal_events(matched_events, temporal_matches)[:limit],
        _sort_temporal_events(context_events, temporal_matches)[:limit],
        temporal_matches,
    )


def _cluster_context_events_for_related_windows(
    *,
    events: tuple[object, ...],
    episode: ResonanceEpisode,
    related_windows: tuple[SuppressedNearbyMatch, ...],
    matched_events: tuple[object, ...],
    peak_temporal_matches: dict[str, EventTemporalMatch],
    limit: int,
) -> tuple[tuple[object, ...], dict[str, EventTemporalMatch]]:
    cluster_start = min(
        [episode.period_start, *(related.episode.period_start for related in related_windows)]
    )
    cluster_end = max(
        [episode.period_end, *(related.episode.period_end for related in related_windows)]
    )
    cluster_temporal_matches = {
        str(getattr(event, "id", "")): _event_temporal_match(
            event=event,
            window_start=cluster_start,
            window_end=cluster_end,
        )
        for event in events
    }
    matched_ids = {str(getattr(event, "id", "")) for event in matched_events}
    context_events = tuple(
        event
        for event in events
        if str(getattr(event, "id", "")) not in matched_ids
        and _is_cluster_context_event(
            event=event,
            temporal_match=cluster_temporal_matches[str(getattr(event, "id", ""))],
        )
    )
    return (
        _sort_temporal_events(context_events, cluster_temporal_matches)[:limit],
        {**cluster_temporal_matches, **peak_temporal_matches},
    )


def _is_cluster_context_event(
    *,
    event: object,
    temporal_match: EventTemporalMatch,
) -> bool:
    if temporal_match.relation == "outside_window":
        return False
    if _is_ultra_broad_context_event(event=event, temporal_match=temporal_match):
        return False
    if _is_low_value_context_event(event=event, temporal_match=temporal_match):
        return False
    return temporal_match.precision in {
        "exact_date",
        "exact_date_range",
        "month_range",
        "year_range",
    } or _is_context_event(event=event, temporal_match=temporal_match)


def _context_related_windows(
    related_windows: tuple[SuppressedNearbyMatch, ...],
) -> tuple[SuppressedNearbyMatch, ...]:
    return tuple(
        related
        for related in related_windows
        if related.reason.startswith("within_")
    )


def _is_exact_window_event(
    *,
    event: object,
    temporal_match: EventTemporalMatch,
) -> bool:
    event_id = str(getattr(event, "id", ""))
    if is_broad_context_event_id(event_id):
        return False
    return (
        temporal_match.precision in EXACT_WINDOW_EVENT_PRECISIONS
        and temporal_match.relation in EXACT_WINDOW_EVENT_RELATIONS
        and temporal_match.score >= 0.8
    )


def _is_context_event(
    *,
    event: object,
    temporal_match: EventTemporalMatch,
) -> bool:
    if temporal_match.relation == "outside_window":
        return False
    if _is_ultra_broad_context_event(event=event, temporal_match=temporal_match):
        return False
    if _is_low_value_context_event(event=event, temporal_match=temporal_match):
        return False
    event_id = str(getattr(event, "id", ""))
    return (
        is_broad_context_event_id(event_id)
        or temporal_match.precision.startswith("approximate")
        or temporal_match.precision == "open_ended_range"
        or temporal_match.score < 0.8
    )


def _is_ultra_broad_context_event(
    *,
    event: object,
    temporal_match: EventTemporalMatch,
) -> bool:
    event_kind = str(getattr(event, "event_kind", ""))
    if event_kind in POINT_EVENT_KINDS:
        return False
    if temporal_match.precision in EXACT_WINDOW_EVENT_PRECISIONS:
        return False
    return _temporal_interval_days(temporal_match) > MAX_PEAK_CONTEXT_DURATION_DAYS


def _is_low_value_context_event(
    *,
    event: object,
    temporal_match: EventTemporalMatch,
) -> bool:
    category = str(getattr(event, "category", ""))
    geo_scope = str(getattr(event, "geo_scope", ""))
    confidence = float(getattr(event, "confidence_score", 0.0))
    duration_years = max(
        0,
        int(getattr(event, "end_astro_year", 0))
        - int(getattr(event, "start_astro_year", 0)),
    )
    if (
        category == "war"
        and geo_scope in {"regional", "national"}
        and duration_years > LOW_VALUE_REGIONAL_WAR_MAX_YEARS
        and confidence <= 0.82
        and temporal_match.precision.startswith("approximate")
    ):
        return True
    return False


def _sort_temporal_events(
    events: tuple[object, ...],
    temporal_matches: dict[str, EventTemporalMatch],
) -> tuple[object, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                -temporal_matches[str(getattr(event, "id", ""))].score,
                _temporal_interval_days(temporal_matches[str(getattr(event, "id", ""))]),
                -float(getattr(event, "confidence_score", 0.0)),
                str(getattr(event, "id", "")),
            ),
        )
    )


def _temporal_interval_days(temporal_match: EventTemporalMatch) -> int:
    if temporal_match.start is None or temporal_match.end is None:
        return 999999
    return max(0, (temporal_match.end - temporal_match.start).days)


def _event_temporal_match(
    *,
    event: object,
    window_start: date,
    window_end: date,
) -> EventTemporalMatch:
    event_start, event_end, precision = _event_date_interval(event)
    if event_start is None or event_end is None:
        return EventTemporalMatch(
            precision="vague",
            relation="vague_context",
            score=0.1,
        )
    if event_end < window_start or event_start > window_end:
        return EventTemporalMatch(
            precision=precision,
            relation="outside_window",
            score=0.0,
            start=event_start,
            end=event_end,
        )
    if precision == "exact_date":
        relation = "exact_date_in_window"
        score = 1.0
    elif precision in {"exact_date_range", "month_range"}:
        relation = "exact_range_overlaps_window"
        score = 0.9
    elif precision == "open_ended_range":
        relation = "approximate_context"
        duration_days = max(1, (event_end - event_start).days + 1)
        score = _approximate_context_score(duration_days)
    else:
        relation = "approximate_context"
        duration_days = max(1, (event_end - event_start).days + 1)
        score = _approximate_context_score(duration_days)
    return EventTemporalMatch(
        precision=precision,
        relation=relation,
        score=score,
        start=event_start,
        end=event_end,
    )


def _approximate_context_score(duration_days: int) -> float:
    if duration_days <= 370:
        return 0.45
    if duration_days <= 10 * 366:
        return 0.3
    if duration_days <= MAX_PEAK_CONTEXT_DURATION_DAYS:
        return 0.18
    return 0.05


def _event_date_interval(event: object) -> tuple[date | None, date | None, str]:
    display_date = str(getattr(event, "display_date", "")).strip()
    exact_range_match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})\s*(?:to|–|—|/|\s+-\s+)\s*(\d{4}-\d{2}-\d{2})",
        display_date,
    )
    if exact_range_match:
        start = date.fromisoformat(exact_range_match.group(1))
        end = date.fromisoformat(exact_range_match.group(2))
        return (min(start, end), max(start, end), "exact_date_range")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", display_date):
        exact_date = date.fromisoformat(display_date)
        return exact_date, exact_date, "exact_date"
    month_match = re.fullmatch(r"(\d{4})-(\d{2})", display_date)
    if month_match:
        year = int(month_match.group(1))
        month = int(month_match.group(2))
        if 1 <= month <= 12:
            return (
                date(year, month, 1),
                _month_end(year=year, month=month),
                "month_range",
            )
    year_range_match = re.fullmatch(r"(\d{4})\s*[–-]\s*(\d{4})", display_date)
    if year_range_match:
        start_year = int(year_range_match.group(1))
        end_year = int(year_range_match.group(2))
        return (
            date(min(start_year, end_year), 1, 1),
            date(max(start_year, end_year), 12, 31),
            "approximate_year_range",
        )
    open_year_match = re.fullmatch(r"(\d{4})\s*[–-]\s*", display_date)
    if open_year_match:
        start_year = int(open_year_match.group(1))
        end_year = int(getattr(event, "end_astro_year", start_year))
        return date(start_year, 1, 1), date(end_year, 12, 31), "open_ended_range"
    if re.fullmatch(r"\d{4}", display_date):
        year = int(display_date)
        return date(year, 1, 1), date(year, 12, 31), "approximate_year"
    start_year = getattr(event, "start_astro_year", None)
    end_year = getattr(event, "end_astro_year", None)
    if isinstance(start_year, int) and isinstance(end_year, int):
        return date(start_year, 1, 1), date(end_year, 12, 31), "approximate_year_range"
    return None, None, "vague"


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _month_end(*, year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _as_datetime_utc(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return datetime(value.year, value.month, value.day, 12, tzinfo=UTC)


def _resonance_basis_response(
    *,
    provider: object,
    query_state: object,
    historical_dt: datetime,
) -> ResonanceBasisResponse:
    historical_state = provider.compute_state(historical_dt)
    current_drivers = _basis_drivers_for_state(query_state)
    historical_drivers = _basis_drivers_for_state(historical_state)
    shared_labels = _shared_basis_driver_labels(current_drivers, historical_drivers)
    return ResonanceBasisResponse(
        current_date=query_state.datetime_utc.date().isoformat(),
        historical_date=historical_state.datetime_utc.date().isoformat(),
        current_drivers=current_drivers,
        historical_drivers=historical_drivers,
        shared_driver_labels=shared_labels,
    )


def _basis_drivers_for_state(state: object) -> list[ResonanceBasisDriverResponse]:
    vector = vectorize_global_slow(state)
    cycles = (
        vector.cycle_strength_debug_json["primary_cycles"]
        + vector.cycle_strength_debug_json["supporting_cycles"]
    )
    drivers = [
        _basis_driver_from_cycle(cycle)
        for cycle in sorted(
            cycles,
            key=lambda item: (
                str(item.get("role", "")) != "primary",
                -float(item.get("contribution", 0.0)),
            ),
        )
    ]
    for body in REGIME_SIGN_BODIES:
        position = state.position_by_body(body)
        placement = placement_for_longitude(position.longitude_deg)
        drivers.append(
            ResonanceBasisDriverResponse(
                driver_type="sign_regime",
                label=f"{body} in {placement.sign}",
                planets=(body,),
                body=body,
                sign=placement.sign,
            )
        )
    return drivers[:6]


def _basis_driver_from_cycle(cycle: dict[str, object]) -> ResonanceBasisDriverResponse:
    pair = tuple(str(item) for item in cycle.get("pair", ()))
    aspect = str(cycle.get("aspect", ""))
    return ResonanceBasisDriverResponse(
        driver_type="cycle",
        label=f"{'-'.join(pair)} {aspect}".strip(),
        planets=pair,
        aspect=aspect or None,
        orb_deg=(
            float(cycle["orb_deg"]) if isinstance(cycle.get("orb_deg"), (int, float)) else None
        ),
        closeness=(
            float(cycle["closeness"])
            if isinstance(cycle.get("closeness"), (int, float))
            else None
        ),
        contribution=(
            float(cycle["contribution"])
            if isinstance(cycle.get("contribution"), (int, float))
            else None
        ),
    )


def _shared_basis_driver_labels(
    current_drivers: list[ResonanceBasisDriverResponse],
    historical_drivers: list[ResonanceBasisDriverResponse],
) -> list[str]:
    historical_keys = {_basis_driver_key(driver) for driver in historical_drivers}
    return [
        driver.label
        for driver in current_drivers
        if _basis_driver_key(driver) in historical_keys
    ]


def _basis_driver_key(driver: ResonanceBasisDriverResponse) -> tuple[str, object]:
    if driver.driver_type == "cycle":
        return ("cycle", tuple(sorted(driver.planets)), driver.aspect)
    if driver.driver_type == "sign_regime":
        return ("sign_regime", driver.body, driver.sign)
    return (driver.driver_type, driver.label)


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
    temporal_match: EventTemporalMatch | None = None,
) -> HistoricalEventResponse:
    temporal_match = temporal_match or EventTemporalMatch(
        precision="unknown",
        relation="unknown",
        score=0.0,
    )
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
        temporal_precision=temporal_match.precision,
        temporal_relation=temporal_match.relation,
        temporal_match_score=temporal_match.score,
        sources=sources,
    )


app = create_app()
