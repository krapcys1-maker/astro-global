from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.historical.coverage import build_coverage_report
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
from services.resonance.index_builder import build_weekly_index
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID, vectorize_global_slow

MAX_TOP_K = 100
MAX_EPISODES = 20
MAX_EVENTS_PER_EPISODE = 12


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

    @field_validator("date_utc")
    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


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
    narrative_confidence: NarrativeConfidenceResponse


class HistoricalEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
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


class ResonanceSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    vector_version: str
    provider: str
    query_datetime_utc: str
    index_start_utc: str
    index_end_utc: str
    index_rows: int
    primary_cycles: list[dict[str, object]]
    supporting_cycles: list[dict[str, object]]
    episodes: list[ResonanceEpisodeResponse]
    deterministic_summary: DeterministicSummary


def create_app(event_db_path: Path | str = DEFAULT_DUCKDB_PATH) -> FastAPI:
    app = FastAPI(title="Astro Global Core API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "astro-global-core"}

    @app.post("/resonance/search", response_model=ResonanceSearchResponse)
    def resonance_search(request: ResonanceSearchRequest) -> ResonanceSearchResponse:
        if request.profile_id != GLOBAL_SLOW_PROFILE_ID:
            raise HTTPException(status_code=400, detail="Only global_slow_v1 is available.")
        if request.provider != "synthetic":
            raise HTTPException(status_code=400, detail="Only synthetic provider is available.")

        provider = SyntheticEphemerisProvider()
        query_dt = request.date_utc
        start_utc = query_dt - timedelta(days=365 * request.lookback_years)
        end_utc = query_dt + timedelta(days=365 * request.lookahead_years)
        built_index = build_weekly_index(
            provider,
            start_utc,
            end_utc,
            step_days=request.step_days,
        )
        query_state = provider.compute_state(query_dt)
        query_vector = vectorize_global_slow(query_state)
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

        episode_responses = [
            _episode_response(
                episode=episode,
                event_db_path=event_db_path,
                event_window_years=request.event_window_years,
                events_per_episode=request.events_per_episode,
            )
            for episode in episodes
        ]
        primary_cycles = query_vector.cycle_strength_debug_json["primary_cycles"]
        supporting_cycles = query_vector.cycle_strength_debug_json["supporting_cycles"]

        return ResonanceSearchResponse(
            profile_id=query_vector.profile_id,
            vector_version=query_vector.vector_version,
            provider=query_state.ephemeris_version,
            query_datetime_utc=query_state.datetime_utc.isoformat(),
            index_start_utc=start_utc.isoformat(),
            index_end_utc=end_utc.isoformat(),
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


def _episode_response(
    *,
    episode: object,
    event_db_path: Path | str,
    event_window_years: int,
    events_per_episode: int,
) -> ResonanceEpisodeResponse:
    events = find_events_overlapping_years(
        start_astro_year=episode.period_start.year - event_window_years,
        end_astro_year=episode.period_end.year + event_window_years,
        db_path=event_db_path,
        limit=events_per_episode,
    )
    event_ids = tuple(event.id for event in events)
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
    coverage = build_coverage_report(events)
    confidence = build_narrative_confidence(
        events=events,
        sources_by_event=sources_by_event,
        coverage_warning=coverage.warning,
        requested_event_limit=events_per_episode,
    )
    return ResonanceEpisodeResponse(
        period_start=episode.period_start.isoformat(),
        period_end=episode.period_end.isoformat(),
        best_date=episode.best_date.isoformat(),
        best_score=episode.best_score,
        best_percentile=episode.best_percentile,
        row_indices=episode.row_indices,
        matched_events=[
            HistoricalEventResponse(
                event_id=event.id,
                title=event.title,
                display_date=event.display_date,
                start_astro_year=event.start_astro_year,
                end_astro_year=event.end_astro_year,
                category=event.category,
                region=event.region,
                geo_scope=event.geo_scope,
                source_url=str(event.source_url),
                confidence_score=event.confidence_score,
                sources=sources_by_event.get(event.id, []),
            )
            for event in events
        ],
        event_coverage=EventCoverageResponse(**coverage.model_dump()),
        narrative_confidence=NarrativeConfidenceResponse(
            event_coverage_score=confidence.event_coverage_score,
            source_quality_score=confidence.source_quality_score,
            evidence_confidence=confidence.evidence_confidence,
            narrative_confidence=confidence.narrative_confidence,
        ),
    )


app = create_app()
