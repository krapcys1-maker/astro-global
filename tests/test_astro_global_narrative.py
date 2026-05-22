from __future__ import annotations

from services.api.app import (
    EventCoverageResponse,
    HistoricalEventResponse,
    ResonanceEpisodeResponse,
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
            )
        ],
        event_coverage=EventCoverageResponse(
            events_found=1,
            regions={"Global": 1},
            categories={"epidemic": 1},
            dominant_region_bias="Global",
            warning="Historical source coverage is uneven for this period.",
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
