from __future__ import annotations

import pytest

from services.api.app import EventSourceResponse, HistoricalEventResponse
from services.narrative.confidence import (
    build_narrative_confidence,
    event_coverage_score,
    load_source_quality_weights,
    source_quality_score,
)


def test_event_coverage_score_penalizes_warning() -> None:
    assert event_coverage_score(events_found=3, requested_event_limit=4, has_warning=False) == 0.75
    assert event_coverage_score(
        events_found=3, requested_event_limit=4, has_warning=True
    ) == pytest.approx(0.4875)


def test_source_quality_score_requires_sources() -> None:
    assert source_quality_score({"evt_missing": []}) == 0.0
    assert source_quality_score(
        {
            "evt_ok": [
                EventSourceResponse(
                    source_id="src_evt_ok_wikidata",
                    source_type="structured_knowledge_base",
                    source_name="Wikidata",
                    source_url="https://www.wikidata.org/wiki/Q1",
                    source_quality="wikidata_seed",
                )
            ]
        }
    ) == pytest.approx(0.65)


def test_source_quality_weights_are_loaded_from_yaml(tmp_path) -> None:
    path = tmp_path / "source_quality.yaml"
    path.write_text(
        "\n".join(
            [
                "source_quality_weights:",
                "  primary: 1.0",
                "  wikidata_seed: 0.25",
                "  unknown: 0.0",
            ]
        ),
        encoding="utf-8",
    )
    weights = load_source_quality_weights(path)

    assert weights["primary"] == pytest.approx(1.0)
    assert source_quality_score(
        {
            "evt_ok": [
                EventSourceResponse(
                    source_id="src_evt_ok_wikidata",
                    source_type="structured_knowledge_base",
                    source_name="Wikidata",
                    source_url="https://www.wikidata.org/wiki/Q1",
                    source_quality="wikidata_seed",
                )
            ]
        },
        weights=weights,
    ) == pytest.approx(0.25)


def test_build_narrative_confidence_stays_separate_from_planetary_score() -> None:
    event = HistoricalEventResponse(
        event_id="evt_ok",
        title="Example",
        display_date="2020",
        start_astro_year=2020,
        end_astro_year=2020,
        category="test",
        event_kind="instant_event",
        region="Global",
        geo_scope="global",
        source_url="https://www.wikidata.org/wiki/Q1",
        confidence_score=0.8,
        sources=[
            EventSourceResponse(
                source_id="src_evt_ok_wikidata",
                source_type="structured_knowledge_base",
                source_name="Wikidata",
                source_url="https://www.wikidata.org/wiki/Q1",
                source_quality="wikidata_seed",
            )
        ],
    )

    confidence = build_narrative_confidence(
        events=[event],
        sources_by_event={"evt_ok": event.sources},
        coverage_warning=None,
        requested_event_limit=2,
    )

    assert confidence.event_coverage_score == pytest.approx(0.5)
    assert confidence.source_quality_score == pytest.approx(0.65)
    assert confidence.evidence_confidence == pytest.approx(0.8)
    assert confidence.narrative_confidence == pytest.approx(0.62)
