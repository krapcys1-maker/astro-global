from __future__ import annotations

from pathlib import Path

from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    event_sources_from_events,
    load_curated_events,
)
from services.historical.events import EventSource, HistoricalEvent

DEFAULT_DUCKDB_PATH = Path("data/duckdb/astro_global.duckdb")
EVENT_KIND_RANKS = {
    "instant_event": 0,
    "short_event": 1,
    "crisis": 1,
    "revolution": 2,
    "war": 2,
    "transition": 3,
    "institution": 4,
    "long_process": 5,
}


def _event_duration_years(event: HistoricalEvent) -> int:
    return event.end_astro_year - event.start_astro_year


def _sort_events_for_query(events: tuple[HistoricalEvent, ...]) -> tuple[HistoricalEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                EVENT_KIND_RANKS.get(event.event_kind, 9),
                -event.confidence_score,
                _event_duration_years(event),
                event.start_astro_year,
                event.id,
            ),
        )
    )


def _sort_sources_for_query(sources: tuple[EventSource, ...]) -> tuple[EventSource, ...]:
    return tuple(
        sorted(
            sources,
            key=lambda source: (source.event_id, source.source_quality, source.id),
        )
    )


def _event_from_row(row: tuple[object, ...]) -> HistoricalEvent:
    return HistoricalEvent(
        id=str(row[0]),
        title=str(row[1]),
        display_date=str(row[2]),
        start_astro_year=int(row[3]),
        end_astro_year=int(row[4]),
        category=str(row[5]),
        event_kind=str(row[6]),
        region=str(row[7]),
        geo_scope=str(row[8]),
        source_url=str(row[9]),
        confidence_score=float(row[10]),
        schema_version=str(row[11]),
    )


def _source_from_row(row: tuple[object, ...]) -> EventSource:
    return EventSource(
        id=str(row[0]),
        event_id=str(row[1]),
        source_type=str(row[2]),
        source_name=str(row[3]),
        source_url=str(row[4]),
        source_quality=str(row[5]),
    )


def find_events_overlapping_years(
    *,
    start_astro_year: int,
    end_astro_year: int,
    db_path: Path | str = DEFAULT_DUCKDB_PATH,
    limit: int = 8,
    fallback_to_curated_csv: bool = True,
) -> tuple[HistoricalEvent, ...]:
    if end_astro_year < start_astro_year:
        msg = "end_astro_year must be >= start_astro_year"
        raise ValueError(msg)

    path = Path(db_path)
    if not path.exists():
        if not fallback_to_curated_csv:
            return ()
        matching_events = tuple(
            event
            for event in load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
            if event.start_astro_year <= end_astro_year and event.end_astro_year >= start_astro_year
        )
        return _sort_events_for_query(matching_events)[:limit]

    try:
        import duckdb
    except ModuleNotFoundError as exc:
        msg = "DuckDB support requires the project dependency 'duckdb'."
        raise RuntimeError(msg) from exc

    with duckdb.connect(str(path), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
              id,
              title,
              display_date,
              start_astro_year,
              end_astro_year,
              category,
              event_kind,
              region,
              geo_scope,
              source_url,
              confidence_score,
              schema_version
            FROM historical_event
            WHERE start_astro_year <= ?
              AND end_astro_year >= ?
            ORDER BY
              CASE event_kind
                WHEN 'instant_event' THEN 0
                WHEN 'short_event' THEN 1
                WHEN 'crisis' THEN 1
                WHEN 'revolution' THEN 2
                WHEN 'war' THEN 2
                WHEN 'transition' THEN 3
                WHEN 'institution' THEN 4
                WHEN 'long_process' THEN 5
                ELSE 9
              END ASC,
              confidence_score DESC,
              (end_astro_year - start_astro_year) ASC,
              start_astro_year ASC,
              id ASC
            LIMIT ?
            """,
            [end_astro_year, start_astro_year, limit],
        ).fetchall()
    return tuple(_event_from_row(row) for row in rows)


def find_sources_for_event_ids(
    *,
    event_ids: tuple[str, ...],
    db_path: Path | str = DEFAULT_DUCKDB_PATH,
    fallback_to_curated_csv: bool = True,
) -> tuple[EventSource, ...]:
    if not event_ids:
        return ()

    path = Path(db_path)
    if not path.exists():
        if not fallback_to_curated_csv:
            return ()
        sources = event_sources_from_events(load_curated_events(DEFAULT_CURATED_EVENTS_PATH))
        requested = set(event_ids)
        return _sort_sources_for_query(
            tuple(source for source in sources if source.event_id in requested)
        )

    try:
        import duckdb
    except ModuleNotFoundError as exc:
        msg = "DuckDB support requires the project dependency 'duckdb'."
        raise RuntimeError(msg) from exc

    placeholders = ", ".join("?" for _ in event_ids)
    with duckdb.connect(str(path), read_only=True) as connection:
        rows = connection.execute(
            f"""
            SELECT
              id,
              event_id,
              source_type,
              source_name,
              source_url,
              source_quality
            FROM event_source
            WHERE event_id IN ({placeholders})
            ORDER BY event_id ASC, source_quality ASC, id ASC
            """,
            list(event_ids),
        ).fetchall()
    return tuple(_source_from_row(row) for row in rows)
