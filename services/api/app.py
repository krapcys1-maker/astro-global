from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ephemeris.provider import PlanetaryPosition
from services.ephemeris.swiss_provider import SwissEphemerisProvider
from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.coverage import build_coverage_report
from services.historical.curated_importer import DEFAULT_CURATED_EVENTS_PATH, load_curated_events
from services.historical.event_query import (
    DEFAULT_DUCKDB_PATH,
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
DEFAULT_DEV_SESSION_TOKEN = "dev-local-token"
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
    lookback_years: int = Field(default=10, ge=1, le=200)
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


class EventCoverageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    events_found: int
    regions: dict[str, int]
    categories: dict[str, int]
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
    primary_cycles: list[dict[str, object]]
    supporting_cycles: list[dict[str, object]]
    episodes: list[ResonanceEpisodeResponse]
    deterministic_summary: DeterministicSummary


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
    fallback_to_curated_csv: bool


class ApiSecurityStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    auth_required: bool
    token_header: str
    cors_allowed_origins: tuple[str, ...]


class DataStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    profiles: tuple[str, ...]
    vector_versions: tuple[str, ...]
    providers: ProviderStatusResponse
    data_store: DataStoreStatusResponse
    security: ApiSecurityStatusResponse


def create_app(
    event_db_path: Path | str = DEFAULT_DUCKDB_PATH,
    *,
    vector_index_root: Path | str = DEFAULT_VECTOR_INDEX_ROOT,
    session_token: str | None = None,
    cors_allowed_origins: tuple[str, ...] = LOCAL_CORS_ORIGINS,
    require_auth: bool = True,
) -> FastAPI:
    app = FastAPI(title="Astro Global Core API", version="0.1.0")
    resolved_session_token = session_token or os.getenv(
        "ASTRO_GLOBAL_SESSION_TOKEN", DEFAULT_DEV_SESSION_TOKEN
    )
    app.state.session_token = resolved_session_token
    app.state.require_auth = require_auth
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_allowed_origins),
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
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "astro-global-core"}

    @app.get("/data/status", response_model=DataStatusResponse)
    def data_status() -> DataStatusResponse:
        return _data_status_response(
            event_db_path=event_db_path,
            auth_required=app.state.require_auth,
            cors_allowed_origins=cors_allowed_origins,
        )

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
        if request.profile_id != GLOBAL_SLOW_PROFILE_ID:
            raise HTTPException(status_code=400, detail="Only global_slow_v1 is available.")

        provider = _build_provider(request.provider)
        query_dt = request.date_utc
        start_utc = query_dt - timedelta(days=365 * request.lookback_years)
        end_utc = query_dt + timedelta(days=365 * request.lookahead_years)
        query_state = provider.compute_state(query_dt)
        query_vector = vectorize_global_slow(query_state)
        built_index, index_source, index_artifact = _load_or_build_index(
            request=request,
            provider=provider,
            start_utc=start_utc,
            end_utc=end_utc,
            ephemeris_version=query_state.ephemeris_version,
            vector_index_root=vector_index_root,
        )
        hits = exact_search(built_index.matrix, query_vector.vector, top_k=request.top_k)
        points = [
            CandidatePoint(
                date=built_index.rows[hit.row_index].datetime_utc.date(),
                score=hit.score,
                row_index=hit.row_index,
                percentile=hit.percentile,
            )
            for hit in hits
        ]
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

    return app


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
) -> tuple[BuiltIndex, str, str | None]:
    if request.index_file is None:
        return (
            build_weekly_index(provider, start_utc, end_utc, step_days=request.step_days),
            "in_memory",
            None,
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
    return built_index, "persistent_npz", request.index_file


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
    if first != start_utc:
        raise HTTPException(status_code=400, detail="Index start does not match request.")
    if last > end_utc or last + timedelta(days=request.step_days) <= end_utc:
        raise HTTPException(status_code=400, detail="Index end does not match request.")


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


def _data_status_response(
    *,
    event_db_path: Path | str,
    auth_required: bool,
    cors_allowed_origins: tuple[str, ...],
) -> DataStatusResponse:
    swiss_import_error = None
    swiss_available = importlib.util.find_spec("swisseph") is not None
    if not swiss_available:
        swiss_import_error = "Python module 'swisseph' is not installed."
    curated_events = load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
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
            fallback_to_curated_csv=True,
        ),
        security=ApiSecurityStatusResponse(
            auth_required=auth_required,
            token_header=SESSION_TOKEN_HEADER,
            cors_allowed_origins=cors_allowed_origins,
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
    events = find_events_overlapping_years(
        start_astro_year=episode.period_start.year - event_window_years,
        end_astro_year=episode.period_end.year + event_window_years,
        db_path=event_db_path,
        limit=events_per_episode,
    )
    sources_by_event = _sources_by_event(
        event_ids=tuple(event.id for event in events),
        event_db_path=event_db_path,
    )
    coverage = build_coverage_report(events)
    confidence = build_narrative_confidence(
        events=events,
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
            for event in events
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
        region=event.region,
        geo_scope=event.geo_scope,
        source_url=str(event.source_url),
        confidence_score=event.confidence_score,
        sources=sources,
    )


app = create_app()
