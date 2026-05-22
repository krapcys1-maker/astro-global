from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ephemeris.synthetic_provider import SyntheticEphemerisProvider
from services.resonance.episode_clustering import CandidatePoint, cluster_candidate_points
from services.resonance.exact_search import exact_search
from services.resonance.index_builder import build_weekly_index
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID, vectorize_global_slow

MAX_TOP_K = 100
MAX_EPISODES = 20


class ResonanceSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_utc: datetime
    profile_id: str = GLOBAL_SLOW_PROFILE_ID
    lookback_years: int = Field(default=10, ge=1, le=200)
    lookahead_years: int = Field(default=2, ge=0, le=50)
    step_days: int = Field(default=7, ge=1, le=31)
    top_k: int = Field(default=30, ge=1, le=MAX_TOP_K)
    max_episodes: int = Field(default=8, ge=1, le=MAX_EPISODES)
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


def create_app() -> FastAPI:
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

        return ResonanceSearchResponse(
            profile_id=query_vector.profile_id,
            vector_version=query_vector.vector_version,
            provider=query_state.ephemeris_version,
            query_datetime_utc=query_state.datetime_utc.isoformat(),
            index_start_utc=start_utc.isoformat(),
            index_end_utc=end_utc.isoformat(),
            index_rows=len(built_index.rows),
            primary_cycles=query_vector.cycle_strength_debug_json["primary_cycles"],
            supporting_cycles=query_vector.cycle_strength_debug_json["supporting_cycles"],
            episodes=[
                ResonanceEpisodeResponse(
                    period_start=episode.period_start.isoformat(),
                    period_end=episode.period_end.isoformat(),
                    best_date=episode.best_date.isoformat(),
                    best_score=episode.best_score,
                    best_percentile=episode.best_percentile,
                    row_indices=episode.row_indices,
                )
                for episode in episodes
            ],
        )

    return app


app = create_app()
