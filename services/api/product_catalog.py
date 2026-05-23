from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from services.api.schemas import (
    ArticleSeedResponse,
    ArticleSeedsResponse,
    ComparePresetEventResponse,
    ResonanceComparePresetResponse,
    ResonanceComparePresetsResponse,
    ResonanceCompareRequest,
)
from services.historical.curated_importer import load_curated_events
from services.resonance.vectorizer import GLOBAL_SLOW_PROFILE_ID

COMPARE_PRESET_DEFINITIONS = (
    {
        "preset_id": "revolutionary_wave_1789_1848",
        "label": "French Revolution vs Revolutions of 1848",
        "left_event_id": "evt_french_revolution",
        "right_event_id": "evt_revolutions_1848",
    },
    {
        "preset_id": "world_wars_1914_1939",
        "label": "World War I vs World War II",
        "left_event_id": "evt_world_war_i",
        "right_event_id": "evt_world_war_ii",
    },
    {
        "preset_id": "modern_crisis_2019_2022",
        "label": "COVID-19 pandemic vs Russian invasion of Ukraine",
        "left_event_id": "evt_covid_19_pandemic",
        "right_event_id": "evt_russian_invasion_ukraine",
    },
)
ARTICLE_SEED_DEFINITIONS = (
    {
        "seed_id": "article_revolutionary_wave_1789_1848",
        "title": "French Revolution and 1848 as a compare research seed",
        "summary": "A seed-only topic for comparing two curated revolutionary wave events.",
        "compare_preset_id": "revolutionary_wave_1789_1848",
    },
    {
        "seed_id": "article_world_wars_1914_1939",
        "title": "World War I and World War II as a compare research seed",
        "summary": "A seed-only topic for comparing two curated global war events.",
        "compare_preset_id": "world_wars_1914_1939",
    },
    {
        "seed_id": "article_modern_crisis_2019_2022",
        "title": "COVID-19 and the Russian invasion of Ukraine as a compare research seed",
        "summary": "A seed-only topic for comparing two curated modern crisis events.",
        "compare_preset_id": "modern_crisis_2019_2022",
    },
)


def resonance_compare_presets_response(
    *,
    required_index_file: str,
) -> ResonanceComparePresetsResponse:
    events_by_id = {event.id: event for event in load_curated_events()}
    missing_event_ids = sorted(
        {
            str(definition["left_event_id"])
            for definition in COMPARE_PRESET_DEFINITIONS
            if str(definition["left_event_id"]) not in events_by_id
        }
        | {
            str(definition["right_event_id"])
            for definition in COMPARE_PRESET_DEFINITIONS
            if str(definition["right_event_id"]) not in events_by_id
        }
    )
    if missing_event_ids:
        missing_detail = ", ".join(missing_event_ids)
        raise HTTPException(
            status_code=500,
            detail=f"Compare presets reference missing curated events: {missing_detail}",
        )

    presets = []
    for definition in COMPARE_PRESET_DEFINITIONS:
        left_event = events_by_id[str(definition["left_event_id"])]
        right_event = events_by_id[str(definition["right_event_id"])]
        left_date = _event_year_start_utc(left_event)
        right_date = _event_year_start_utc(right_event)
        presets.append(
            ResonanceComparePresetResponse(
                preset_id=str(definition["preset_id"]),
                label=str(definition["label"]),
                left_event=_compare_preset_event_response(left_event),
                right_event=_compare_preset_event_response(right_event),
                compare_request=ResonanceCompareRequest(
                    left_date_utc=left_date,
                    right_date_utc=right_date,
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
                warnings=(
                    "Preset dates are backend-authored from curated event start years.",
                    (
                        "Date precision is year_start_anchor unless a future curated "
                        "layer adds exact dates."
                    ),
                    "This is a comparison preset, not a prediction.",
                ),
            )
        )
    return ResonanceComparePresetsResponse(
        service="astro-global-core",
        provider="swiss",
        index_file=required_index_file,
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        date_policy="curated_start_year_to_utc_year_start",
        presets=tuple(presets),
    )


def article_seeds_response(*, required_index_file: str) -> ArticleSeedsResponse:
    compare_presets = resonance_compare_presets_response(
        required_index_file=required_index_file,
    )
    presets_by_id = {preset.preset_id: preset for preset in compare_presets.presets}
    missing_preset_ids = sorted(
        str(definition["compare_preset_id"])
        for definition in ARTICLE_SEED_DEFINITIONS
        if str(definition["compare_preset_id"]) not in presets_by_id
    )
    if missing_preset_ids:
        missing_detail = ", ".join(missing_preset_ids)
        raise HTTPException(
            status_code=500,
            detail=f"Article seeds reference missing compare presets: {missing_detail}",
        )

    seeds = []
    for definition in ARTICLE_SEED_DEFINITIONS:
        compare_preset_id = str(definition["compare_preset_id"])
        preset = presets_by_id[compare_preset_id]
        seeds.append(
            ArticleSeedResponse(
                seed_id=str(definition["seed_id"]),
                title=str(definition["title"]),
                summary=str(definition["summary"]),
                seed_kind="compare_research_seed",
                editorial_status="seed_only_not_article",
                compare_preset_id=compare_preset_id,
                source_event_ids=(
                    preset.left_event.event_id,
                    preset.right_event.event_id,
                ),
                source_event_titles=(
                    preset.left_event.title,
                    preset.right_event.title,
                ),
                compare_request=preset.compare_request,
                allowed_next_api_calls=(
                    "GET /resonance/compare/presets",
                    "POST /resonance/compare",
                ),
                warnings=(
                    "This endpoint returns article seeds only, not generated articles.",
                    "AI must not add facts or events outside backend responses.",
                    "Human editorial review is required before publication.",
                ),
            )
        )
    return ArticleSeedsResponse(
        service="astro-global-core",
        provider=compare_presets.provider,
        index_file=compare_presets.index_file,
        profile_id=compare_presets.profile_id,
        content_policy="seed_only_no_generated_article_text",
        seeds=tuple(seeds),
    )


def _compare_preset_event_response(event: object) -> ComparePresetEventResponse:
    event_date = _event_year_start_utc(event)
    return ComparePresetEventResponse(
        event_id=event.id,
        title=event.title,
        display_date=event.display_date,
        start_astro_year=event.start_astro_year,
        end_astro_year=event.end_astro_year,
        category=event.category,
        event_kind=event.event_kind,
        confidence_score=event.confidence_score,
        date_utc=_utc_z_string(event_date),
        date_precision="year_start_anchor",
    )


def _event_year_start_utc(event: object) -> datetime:
    return datetime(event.start_astro_year, 1, 1, tzinfo=UTC)


def _utc_z_string(dt_utc: datetime) -> str:
    return dt_utc.astimezone(UTC).isoformat().replace("+00:00", "Z")
