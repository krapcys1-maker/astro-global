from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from scripts.report_reliable_history_coverage import (
    build_reliable_history_coverage_report,
    render_reliable_history_coverage_markdown,
)
from services.historical.coverage import build_coverage_report
from services.historical.curated_importer import (
    event_sources_from_events,
    load_curated_event_sources,
    load_curated_events,
    sort_curated_events,
    validate_curated_events_stable_order,
    write_events_to_duckdb,
)
from services.historical.data_bias import (
    DOMINANT_CATEGORY_THRESHOLD,
    DOMINANT_EVENT_KIND_THRESHOLD,
    MIN_PRIMARY_OR_INSTITUTIONAL_SOURCE_SHARE,
    build_historical_data_bias_report,
    render_historical_data_bias_markdown,
)
from services.historical.event_query import (
    find_event_selection_overlapping_years,
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


def test_curated_events_are_in_stable_chronological_order() -> None:
    events = load_curated_events()

    validate_curated_events_stable_order(events)


def test_reliable_history_coverage_report_tracks_1500_to_1900() -> None:
    events = load_curated_events()
    report = build_reliable_history_coverage_report(
        events=events,
        sources=event_sources_from_events(events),
    )

    assert report["range_label"] == "reliable_history_1500_1900"
    assert [century["label"] for century in report["centuries"]] == [
        "1500-1599",
        "1600-1699",
        "1700-1799",
        "1800-1899",
    ]
    assert all(century["event_count"] > 0 for century in report["centuries"])
    assert all(century["source_count"] >= century["event_count"] for century in report["centuries"])
    assert [century["context_event_count"] for century in report["centuries"]] == [
        0,
        1,
        1,
        1,
    ]
    rendered = render_reliable_history_coverage_markdown(report)
    assert "Reliable History Coverage 1500-1900" in rendered
    assert tuple(event.id for event in events) == tuple(
        event.id for event in sort_curated_events(events)
    )


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


def test_long_process_events_span_multiple_years() -> None:
    events = load_curated_events()
    zero_duration_long_processes = tuple(
        event.id
        for event in events
        if event.event_kind == "long_process"
        and event.start_astro_year == event.end_astro_year
    )

    assert zero_duration_long_processes == ()


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
    assert all(source.source_precision == "direct" for source in sources)
    assert all(sources_by_event[event.id] for event in events)


def test_curated_event_sources_do_not_keep_weak_precision_rows() -> None:
    sources = load_curated_event_sources()

    assert {
        source.id
        for source in sources
        if source.source_precision in {"broad_context", "contextual"}
    } == set()


def test_historical_data_bias_report_confirms_current_seed_balance() -> None:
    events = load_curated_events()
    report = build_historical_data_bias_report(
        events=events,
        sources=event_sources_from_events(events),
    )

    assert report.events_count >= 150
    assert report.sources_count > report.events_count
    assert report.start_astro_year_min == 1501
    assert report.ongoing_events_count >= 6
    assert report.categories[0].label == "war"
    assert report.categories[0].share < 0.35
    assert report.event_kinds[0].share < 0.35
    assert report.warnings == ()


def test_curated_events_bias_guardrails_stay_under_ci_thresholds() -> None:
    events = load_curated_events()
    report = build_historical_data_bias_report(
        events=events,
        sources=event_sources_from_events(events),
    )

    category_breaches = [
        f"{bucket.label}={bucket.share:.1%}"
        for bucket in report.categories
        if bucket.share >= DOMINANT_CATEGORY_THRESHOLD
    ]
    event_kind_breaches = [
        f"{bucket.label}={bucket.share:.1%}"
        for bucket in report.event_kinds
        if bucket.share >= DOMINANT_EVENT_KIND_THRESHOLD
    ]
    source_quality = {bucket.label: bucket.share for bucket in report.source_quality}
    primary_or_institutional_share = source_quality.get("primary", 0.0) + source_quality.get(
        "institutional",
        0.0,
    )

    assert category_breaches == []
    assert event_kind_breaches == []
    assert primary_or_institutional_share >= MIN_PRIMARY_OR_INSTITUTIONAL_SOURCE_SHARE


def test_historical_data_bias_report_renders_markdown() -> None:
    events = load_curated_events()
    report = build_historical_data_bias_report(
        events=events,
        sources=event_sources_from_events(events),
    )
    rendered = render_historical_data_bias_markdown(report)

    assert "# Raport biasu danych historycznych - Astro Global" in rendered
    assert "| war |" in rendered
    assert "Brak ostrzezen biasu" in rendered
    assert "Primary/institutional source share is low" not in rendered


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
        "evt_first_italo_ethiopian_war",
        "evt_xray_discovery",
    }


def test_find_events_prioritizes_long_process_boundaries_over_background() -> None:
    events = find_events_overlapping_years(
        start_astro_year=1882,
        end_astro_year=1885,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=6,
    )

    ids = [event.id for event in events]

    assert "evt_berlin_conference" in ids
    assert ids.index("evt_berlin_conference") < ids.index("evt_scramble_for_africa")


def test_find_events_surfaces_pre1900_start_markers_without_dropping_broad_processes() -> None:
    events_by_id = {event.id: event for event in load_curated_events()}

    assert events_by_id["evt_sokoto_caliphate"].event_kind == "long_process"
    assert events_by_id["evt_french_conquest_algeria"].event_kind == "long_process"

    sokoto_events = find_events_overlapping_years(
        start_astro_year=1804,
        end_astro_year=1804,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=6,
    )
    algeria_events = find_events_overlapping_years(
        start_astro_year=1830,
        end_astro_year=1830,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=6,
    )

    assert "evt_sokoto_jihad_start" in {event.id for event in sokoto_events}
    assert "evt_invasion_algiers_1830" in {event.id for event in algeria_events}


def test_find_events_balances_point_events_with_historical_context() -> None:
    events = find_events_overlapping_years(
        start_astro_year=1966,
        end_astro_year=1970,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=6,
    )

    ids = {event.id for event in events}
    point_event_count = sum(
        event.event_kind in {"instant_event", "short_event", "crisis", "institution"}
        for event in events
    )

    assert len(events) == 6
    assert point_event_count <= 3
    assert ids >= {"evt_cultural_revolution", "evt_vietnam_war"}


def test_find_events_limits_ongoing_events_when_finished_context_exists() -> None:
    events = find_events_overlapping_years(
        start_astro_year=2019,
        end_astro_year=2023,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=6,
    )

    ids = {event.id for event in events}
    ongoing_count = sum(event.is_ongoing for event in events)

    assert len(events) == 6
    assert ongoing_count <= 2
    assert "evt_covid_19_pandemic" in ids
    assert ids & {"evt_chatgpt_launch", "evt_dart_impact", "evt_jwst_launch"}


def test_find_event_selection_returns_omitted_point_event_overflow() -> None:
    events, omitted_point_events = find_event_selection_overlapping_years(
        start_astro_year=2019,
        end_astro_year=2023,
        db_path=Path("data/duckdb/missing-for-test.duckdb"),
        limit=4,
        omitted_point_event_limit=3,
    )

    event_ids = {event.id for event in events}
    omitted_ids = {event.id for event in omitted_point_events}

    assert len(events) == 4
    assert 1 <= len(omitted_point_events) <= 3
    assert event_ids.isdisjoint(omitted_ids)
    assert all(
        event.event_kind in {"instant_event", "short_event", "crisis", "institution"}
        for event in omitted_point_events
    )


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
    assert {source.source_name for source in sources} >= {
        "Centers for Disease Control and Prevention",
        "Wikidata",
    }


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
