from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.narrative.deterministic_summary import DeterministicSummary
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID

MAX_TOP_K = 100
MAX_EPISODES = 20
MAX_EVENTS_PER_EPISODE = 12
MAX_EVENTS_WINDOW = 100


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
    historical_analogue_mode: bool = False
    exclude_same_calendar_year: bool = True
    local_resonance_window_days: int = Field(default=365, ge=0, le=3650)
    historical_analogue_min_year_gap: int = Field(default=5, ge=0, le=100)
    historical_exclude_active_regime_windows: bool = True

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


class HistoricalAnaloguePolicyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    historical_analogue_mode: bool
    exclude_same_calendar_year: bool
    local_resonance_window_days: int
    historical_analogue_min_year_gap: int
    historical_exclude_active_regime_windows: bool
    local_resonance_excluded: bool
    excluded_local_episodes_count: int


class ActiveRegimeWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    driver_id: str
    driver_type: str
    label: str
    start_date: str
    end_date: str
    source: str


class ActiveCycleWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cycle_id: str
    planets: tuple[str, ...]
    aspect: str
    role: str
    label: str
    start_date: str
    peak_date: str | None
    end_date: str
    orb_at_query: float | None
    closeness_at_query: float | None
    confidence_scope: str


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
    historical_analogues: list[ResonanceEpisodeResponse] = Field(default_factory=list)
    local_resonance: ResonanceEpisodeResponse | None = None
    nearby_matches: list[ResonanceEpisodeResponse] = Field(default_factory=list)
    local_resonance_window: list[ResonanceEpisodeResponse] = Field(default_factory=list)
    active_regime_windows: list[ActiveRegimeWindowResponse] = Field(default_factory=list)
    active_background_cycles: list[ActiveRegimeWindowResponse] = Field(default_factory=list)
    active_cycle_windows: list[ActiveCycleWindowResponse] = Field(default_factory=list)
    regime_cycle_windows: list[ActiveCycleWindowResponse] = Field(default_factory=list)
    analogue_policy: HistoricalAnaloguePolicyResponse
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


class ComparePresetEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    event_kind: str
    confidence_score: float
    date_utc: str
    date_precision: str


class ResonanceComparePresetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    preset_id: str
    label: str
    left_event: ComparePresetEventResponse
    right_event: ComparePresetEventResponse
    compare_request: ResonanceCompareRequest
    warnings: tuple[str, ...]


class ResonanceComparePresetsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    provider: str
    index_file: str
    profile_id: str
    date_policy: str
    presets: tuple[ResonanceComparePresetResponse, ...]


class ArticleSeedResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed_id: str
    title: str
    summary: str
    seed_kind: str
    editorial_status: str
    compare_preset_id: str
    source_event_ids: tuple[str, ...]
    source_event_titles: tuple[str, ...]
    compare_request: ResonanceCompareRequest
    allowed_next_api_calls: tuple[str, ...]
    warnings: tuple[str, ...]


class ArticleSeedsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    provider: str
    index_file: str
    profile_id: str
    content_policy: str
    seeds: tuple[ArticleSeedResponse, ...]


class TimelineSeedResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed_id: str
    event_id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    event_kind: str
    region: str
    geo_scope: str
    confidence_score: float
    date_utc: str
    date_precision: str
    search_request: ResonanceSearchRequest
    allowed_next_api_calls: tuple[str, ...]
    warnings: tuple[str, ...]


class TimelineSeedsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str
    provider: str
    index_file: str
    profile_id: str
    reliable_history_start: int
    reliable_history_end: int
    date_policy: str
    selection_policy: str
    seeds: tuple[TimelineSeedResponse, ...]


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
