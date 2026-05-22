from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from services.historical.coverage import build_coverage_report
from services.historical.curated_importer import (
    event_sources_from_events,
    load_curated_event_sources,
    load_curated_events,
    write_events_to_duckdb,
)
from services.historical.event_query import (
    find_events_overlapping_years,
    find_sources_for_event_ids,
)
from services.historical.events import HistoricalEvent


def test_curated_events_load_with_sources() -> None:
    events = load_curated_events()

    assert len(events) >= 150
    assert min(event.start_astro_year for event in events) <= 1517
    assert all(event.source_url for event in events)
    assert all(event.end_astro_year >= event.start_astro_year for event in events)
    assert all(event.event_kind for event in events)
    assert all(event.end_year_policy for event in events)


def test_open_ended_events_are_marked_ongoing() -> None:
    events = load_curated_events()
    open_ended_events = tuple(event for event in events if event.display_date.endswith("-"))

    assert {event.id for event in open_ended_events} >= {
        "evt_covid_19_pandemic",
        "evt_russian_invasion_ukraine",
        "evt_syrian_civil_war",
        "evt_yemeni_civil_war_2014",
        "evt_colombian_conflict",
        "evt_hiv_aids_pandemic",
    }
    assert all(event.is_ongoing for event in open_ended_events)
    assert all(event.end_year_policy == "build_year" for event in open_ended_events)
    assert all(
        event.end_year_policy == "explicit"
        for event in events
        if not event.is_ongoing
    )


def test_open_ended_display_date_cannot_be_non_ongoing() -> None:
    with pytest.raises(ValueError, match="open-ended display_date"):
        HistoricalEvent(
            id="evt_bad_ongoing",
            title="Bad ongoing event",
            display_date="2020-",
            start_astro_year=2020,
            end_astro_year=2026,
            category="test",
            event_kind="crisis",
            region="Global",
            geo_scope="global",
            source_url="https://www.wikidata.org/wiki/Q1",
            confidence_score=0.5,
            is_ongoing=False,
        )


def test_curated_events_cover_multiple_regions_and_categories() -> None:
    events = load_curated_events()

    assert len({event.region for event in events}) >= 6
    assert len({event.category for event in events}) >= 8
    assert {"long_process", "war", "revolution", "instant_event"} <= {
        event.event_kind for event in events
    }


def test_event_sources_are_generated_for_curated_events() -> None:
    events = load_curated_events()
    sources = event_sources_from_events(events)

    assert len(sources) > len(events)
    assert {source.event_id for source in sources} == {event.id for event in events}
    assert sum(source.source_quality == "wikidata_seed" for source in sources) == len(events)
    assert any(source.source_quality == "institutional" for source in sources)
    assert any(source.source_quality == "encyclopedic" for source in sources)


def test_curated_event_sources_load_extra_sources() -> None:
    sources = load_curated_event_sources()
    events = load_curated_events()
    sources_by_event = {event.id: [] for event in events}
    for source in sources:
        sources_by_event.setdefault(source.event_id, []).append(source)

    assert len(sources) >= len(events)
    assert {event.id for event in events} <= {source.event_id for source in sources}
    assert any(source.event_id == "evt_covid_19_pandemic" for source in sources)
    assert all(source.source_quality != "wikidata_seed" for source in sources)
    assert all(source.source_precision for source in sources)
    assert any(source.source_precision == "broad_context" for source in sources)
    assert any(source.source_precision == "contextual" for source in sources)
    assert all(sources_by_event[event.id] for event in events)


def test_contextual_sources_have_direct_curated_backup() -> None:
    sources = load_curated_event_sources()
    weaker_event_ids = {
        source.event_id
        for source in sources
        if source.source_precision in {"broad_context", "contextual"}
    }

    for event_id in weaker_event_ids:
        event_sources = [source for source in sources if source.event_id == event_id]
        assert any(source.source_precision == "direct" for source in event_sources)


def test_curated_events_reject_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    rows = [
        {
            "id": "evt_duplicate",
            "title": "First",
            "display_date": "1900",
            "start_astro_year": "1900",
            "end_astro_year": "1900",
            "category": "test",
            "event_kind": "instant_event",
            "region": "Global",
            "geo_scope": "global",
            "source_url": "https://www.wikidata.org/wiki/Q1",
            "confidence_score": "0.5",
        },
        {
            "id": "evt_duplicate",
            "title": "Second",
            "display_date": "1901",
            "start_astro_year": "1901",
            "end_astro_year": "1901",
            "category": "test",
            "event_kind": "instant_event",
            "region": "Global",
            "geo_scope": "global",
            "source_url": "https://www.wikidata.org/wiki/Q2",
            "confidence_score": "0.5",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="duplicate ids"):
        load_curated_events(path)


def test_coverage_report_warns_on_empty_events() -> None:
    report = build_coverage_report(())

    assert report.events_found == 0
    assert report.event_kinds == {}
    assert report.ongoing_events_count == 0
    assert report.warning == "No historical events found for this period."


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_curated_events_can_be_written_to_duckdb(tmp_path: Path) -> None:
    import duckdb

    db_path = tmp_path / "astro_global.duckdb"
    events = load_curated_events()

    write_events_to_duckdb(db_path, events)

    with duckdb.connect(str(db_path)) as connection:
        count = connection.execute("SELECT count(*) FROM historical_event").fetchone()[0]
        source_count = connection.execute("SELECT count(*) FROM event_source").fetchone()[0]
    assert count == len(events)
    assert source_count > len(events)


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_find_events_overlapping_years_uses_duckdb(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())

    events = find_events_overlapping_years(
        start_astro_year=2020,
        end_astro_year=2026,
        db_path=db_path,
    )

    assert any(event.id == "evt_covid_19_pandemic" for event in events)
    assert all(event.start_astro_year <= 2026 for event in events)


def test_find_events_prioritizes_specific_events_over_long_processes() -> None:
    events = find_events_overlapping_years(
        start_astro_year=1895,
        end_astro_year=1896,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=3,
    )

    assert len(events) == 3
    assert all(event.event_kind != "long_process" for event in events)
    assert {event.id for event in events} >= {
        "evt_first_sino_japanese_war",
        "evt_first_italo_ethiopian_war",
    }


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_find_events_preserves_ongoing_metadata_from_duckdb(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())

    events = find_events_overlapping_years(
        start_astro_year=2022,
        end_astro_year=2026,
        db_path=db_path,
        limit=12,
    )

    ongoing_by_id = {event.id: event for event in events if event.is_ongoing}
    assert ongoing_by_id["evt_russian_invasion_ukraine"].end_year_policy == "build_year"


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_find_events_fallback_matches_duckdb_order(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())

    db_events = find_events_overlapping_years(
        start_astro_year=2020,
        end_astro_year=2026,
        db_path=db_path,
        limit=8,
    )
    fallback_events = find_events_overlapping_years(
        start_astro_year=2020,
        end_astro_year=2026,
        db_path=tmp_path / "missing.duckdb",
        limit=8,
    )

    assert [event.id for event in fallback_events] == [event.id for event in db_events]


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_find_sources_for_event_ids_uses_duckdb(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())

    sources = find_sources_for_event_ids(
        event_ids=("evt_covid_19_pandemic",),
        db_path=db_path,
    )

    assert len(sources) >= 2
    assert {source.event_id for source in sources} == {"evt_covid_19_pandemic"}
    assert {source.source_name for source in sources} >= {"Wikidata", "World Health Organization"}


@pytest.mark.skipif(importlib.util.find_spec("duckdb") is None, reason="duckdb is not installed")
def test_find_sources_fallback_matches_duckdb_order(tmp_path: Path) -> None:
    db_path = tmp_path / "astro_global.duckdb"
    write_events_to_duckdb(db_path, load_curated_events())
    event_ids = ("evt_covid_19_pandemic", "evt_russian_invasion_ukraine")

    db_sources = find_sources_for_event_ids(event_ids=event_ids, db_path=db_path)
    fallback_sources = find_sources_for_event_ids(
        event_ids=event_ids,
        db_path=tmp_path / "missing.duckdb",
    )

    assert [source.id for source in fallback_sources] == [source.id for source in db_sources]
