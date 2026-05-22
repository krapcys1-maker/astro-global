from __future__ import annotations

from services.api.app import (
    EventCoverageResponse,
    EventSourceResponse,
    HistoricalEventResponse,
    NarrativeConfidenceResponse,
    ResonanceEpisodeResponse,
    ScoreBreakdownResponse,
)
from services.narrative.deterministic_summary import build_deterministic_summary


def test_deterministic_summary_uses_only_input_event_ids() -> None:
    episode = ResonanceEpisodeResponse(
        period_start="2026-02-17",
        period_end="2026-06-30",
        best_date="2026-05-21",
        best_score=0.99,
        best_percentile=1.0,
        row_indices=(1, 2, 3),
        matched_events=[
            HistoricalEventResponse(
                event_id="evt_covid_19_pandemic",
                title="COVID-19 pandemic",
                display_date="2019-",
                start_astro_year=2019,
                end_astro_year=2026,
                category="epidemic",
                region="Global",
                geo_scope="global",
                source_url="https://www.wikidata.org/wiki/Q81068910",
                confidence_score=0.75,
                sources=[
                    EventSourceResponse(
                        source_id="src_evt_covid_19_pandemic_wikidata",
                        source_type="structured_knowledge_base",
                        source_name="Wikidata",
                        source_url="https://www.wikidata.org/wiki/Q81068910",
                        source_quality="wikidata_seed",
                    )
                ],
            )
        ],
        event_coverage=EventCoverageResponse(
            events_found=1,
            regions={"Global": 1},
            categories={"epidemic": 1},
            dominant_region_bias="Global",
            warning="Historical source coverage is uneven for this period.",
        ),
        score_breakdown=ScoreBreakdownResponse(
            structural_similarity=0.99,
            cycle_power_score=0.8,
            rarity_adjusted_percentile=1.0,
            planetary_resonance_score=0.944,
            label="strong",
            primary_cycle_count=1,
            strongest_primary_contribution=0.61,
            rare_configuration=True,
            insufficient_comparable_history=False,
        ),
        narrative_confidence=NarrativeConfidenceResponse(
            event_coverage_score=0.65,
            source_quality_score=0.65,
            evidence_confidence=0.75,
            narrative_confidence=0.675,
        ),
    )

    summary = build_deterministic_summary(
        profile_id="global_slow_v1",
        query_datetime_utc="2026-05-22T12:00:00+00:00",
        primary_cycles=[
            {
                "pair": ["Uranus", "Pluto"],
                "aspect": "conjunction",
                "tier": "S_epochal",
                "contribution": 0.61,
            }
        ],
        supporting_cycles=[],
        episodes=[episode],
    )

    assert summary.language == "pl"
    assert summary.referenced_event_ids == ("evt_covid_19_pandemic",)
    assert "evt_covid_19_pandemic" in summary.summary
    assert "To jest opis podobieństwa symboliczno-historycznego" in summary.summary
    assert "na pewno" not in summary.summary.lower()


def test_deterministic_summary_does_not_reference_events_without_sources() -> None:
    episode = ResonanceEpisodeResponse(
        period_start="2026-02-17",
        period_end="2026-06-30",
        best_date="2026-05-21",
        best_score=0.99,
        best_percentile=1.0,
        row_indices=(1,),
        matched_events=[
            HistoricalEventResponse(
                event_id="evt_unsourced",
                title="Unsourced event",
                display_date="2026",
                start_astro_year=2026,
                end_astro_year=2026,
                category="test",
                region="Global",
                geo_scope="global",
                source_url="https://www.wikidata.org/wiki/Q1",
                confidence_score=0.5,
                sources=[],
            )
        ],
        event_coverage=EventCoverageResponse(
            events_found=1,
            regions={"Global": 1},
            categories={"test": 1},
            dominant_region_bias="Global",
            warning=None,
        ),
        score_breakdown=ScoreBreakdownResponse(
            structural_similarity=0.99,
            cycle_power_score=0.0,
            rarity_adjusted_percentile=1.0,
            planetary_resonance_score=0.744,
            label="moderate",
            primary_cycle_count=0,
            strongest_primary_contribution=0.0,
            rare_configuration=False,
            insufficient_comparable_history=False,
        ),
        narrative_confidence=NarrativeConfidenceResponse(
            event_coverage_score=1.0,
            source_quality_score=0.0,
            evidence_confidence=0.5,
            narrative_confidence=0.575,
        ),
    )

    summary = build_deterministic_summary(
        profile_id="global_slow_v1",
        query_datetime_utc="2026-05-22T12:00:00+00:00",
        primary_cycles=[],
        supporting_cycles=[],
        episodes=[episode],
    )

    assert summary.referenced_event_ids == ()
    assert "evt_unsourced" not in summary.summary
