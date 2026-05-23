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
    "crisis": 0,
    "instant_event": 1,
    "short_event": 1,
    "revolution": 2,
    "war": 2,
    "transition": 3,
    "institution": 4,
    "long_process": 5,
}
POINT_EVENT_KINDS = frozenset({"instant_event", "short_event", "crisis", "institution"})
MIN_EVENT_CANDIDATE_LIMIT = 50
ONGOING_EVENT_CAP_SHARE = 1 / 3
DEFAULT_OMITTED_POINT_EVENT_LIMIT = 5


def _event_duration_years(event: HistoricalEvent) -> int:
    return event.end_astro_year - event.start_astro_year


def _event_year_distance(
    event: HistoricalEvent,
    *,
    start_astro_year: int,
    end_astro_year: int,
) -> float:
    center_year = (start_astro_year + end_astro_year) / 2
    if event.start_astro_year <= center_year <= event.end_astro_year:
        return 0.0
    return min(
        abs(event.start_astro_year - center_year),
        abs(event.end_astro_year - center_year),
    )


def _sort_events_for_query(
    events: tuple[HistoricalEvent, ...],
    *,
    start_astro_year: int,
    end_astro_year: int,
) -> tuple[HistoricalEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                EVENT_KIND_RANKS.get(event.event_kind, 9),
                _event_year_distance(
                    event,
                    start_astro_year=start_astro_year,
                    end_astro_year=end_astro_year,
                ),
                -event.confidence_score,
                _event_duration_years(event),
                event.start_astro_year,
                event.id,
            ),
        )
    )


def _candidate_limit(limit: int) -> int:
    return max(limit * 6, limit, MIN_EVENT_CANDIDATE_LIMIT)


def _select_balanced_events(
    events: tuple[HistoricalEvent, ...],
    *,
    limit: int,
) -> tuple[HistoricalEvent, ...]:
    if limit <= 0:
        return ()
    if len(events) <= limit:
        return events

    has_context_events = any(event.event_kind not in POINT_EVENT_KINDS for event in events)
    has_finished_events = any(not event.is_ongoing for event in events)
    point_event_cap = limit if not has_context_events else max(1, limit // 2)
    ongoing_event_cap = (
        limit if not has_finished_events else max(1, int(limit * ONGOING_EVENT_CAP_SHARE))
    )

    selected: list[HistoricalEvent] = []
    deferred_point_events: list[HistoricalEvent] = []
    deferred_ongoing_events: list[HistoricalEvent] = []
    point_event_count = 0
    ongoing_event_count = 0
    for event in events:
        if len(selected) >= limit:
            break
        if event.is_ongoing and ongoing_event_count >= ongoing_event_cap:
            deferred_ongoing_events.append(event)
            continue
        if event.event_kind in POINT_EVENT_KINDS and point_event_count >= point_event_cap:
            deferred_point_events.append(event)
            continue
        selected.append(event)
        if event.event_kind in POINT_EVENT_KINDS:
            point_event_count += 1
        if event.is_ongoing:
            ongoing_event_count += 1

    for event in deferred_point_events:
        if len(selected) >= limit:
            break
        selected.append(event)
        if event.is_ongoing:
            ongoing_event_count += 1

    for event in deferred_ongoing_events:
        if len(selected) >= limit:
            break
        selected.append(event)

    return tuple(selected)


def _omitted_point_events(
    *,
    candidates: tuple[HistoricalEvent, ...],
    selected: tuple[HistoricalEvent, ...],
    limit: int,
) -> tuple[HistoricalEvent, ...]:
    if limit <= 0:
        return ()
    selected_ids = {event.id for event in selected}
    return tuple(
        event
        for event in candidates
        if event.id not in selected_ids and event.event_kind in POINT_EVENT_KINDS
    )[:limit]


def _sort_sources_for_query(sources: tuple[EventSource, ...]) -> tuple[EventSource, ...]:
    return tuple(
        sorted(
            sources,
            key=lambda source: (
                source.event_id,
                source.source_quality,
                source.source_precision,
                source.id,
            ),
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
        is_ongoing=bool(row[11]),
        end_year_policy=str(row[12]),
        schema_version=str(row[13]),
    )


def _source_from_row(row: tuple[object, ...]) -> EventSource:
    return EventSource(
        id=str(row[0]),
        event_id=str(row[1]),
        source_type=str(row[2]),
        source_name=str(row[3]),
        source_url=str(row[4]),
        source_quality=str(row[5]),
        source_precision=str(row[6]),
    )


def find_events_overlapping_years(
    *,
    start_astro_year: int,
    end_astro_year: int,
    db_path: Path | str = DEFAULT_DUCKDB_PATH,
    limit: int = 8,
    fallback_to_curated_csv: bool = True,
) -> tuple[HistoricalEvent, ...]:
    events, _omitted_events = find_event_selection_overlapping_years(
        start_astro_year=start_astro_year,
        end_astro_year=end_astro_year,
        db_path=db_path,
        limit=limit,
        fallback_to_curated_csv=fallback_to_curated_csv,
        omitted_point_event_limit=0,
    )
    return events


def find_event_selection_overlapping_years(
    *,
    start_astro_year: int,
    end_astro_year: int,
    db_path: Path | str = DEFAULT_DUCKDB_PATH,
    limit: int = 8,
    fallback_to_curated_csv: bool = True,
    omitted_point_event_limit: int = DEFAULT_OMITTED_POINT_EVENT_LIMIT,
) -> tuple[tuple[HistoricalEvent, ...], tuple[HistoricalEvent, ...]]:
    if end_astro_year < start_astro_year:
        msg = "end_astro_year must be >= start_astro_year"
        raise ValueError(msg)
    if limit <= 0:
        return (), ()

    path = Path(db_path)
    if not path.exists():
        if not fallback_to_curated_csv:
            return (), ()
        matching_events = tuple(
            event
            for event in load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
            if event.start_astro_year <= end_astro_year and event.end_astro_year >= start_astro_year
        )
        sorted_events = _sort_events_for_query(
            matching_events,
            start_astro_year=start_astro_year,
            end_astro_year=end_astro_year,
        )
        selected_events = _select_balanced_events(sorted_events, limit=limit)
        omitted_events = _omitted_point_events(
            candidates=sorted_events,
            selected=selected_events,
            limit=omitted_point_event_limit,
        )
        return selected_events, omitted_events

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
              is_ongoing,
              end_year_policy,
              schema_version
            FROM historical_event
            WHERE start_astro_year <= ?
              AND end_astro_year >= ?
            ORDER BY
              CASE event_kind
                WHEN 'crisis' THEN 0
                WHEN 'instant_event' THEN 1
                WHEN 'short_event' THEN 1
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
            [end_astro_year, start_astro_year, _candidate_limit(limit)],
        ).fetchall()
    sorted_events = _sort_events_for_query(
        tuple(_event_from_row(row) for row in rows),
        start_astro_year=start_astro_year,
        end_astro_year=end_astro_year,
    )
    selected_events = _select_balanced_events(sorted_events, limit=limit)
    omitted_events = _omitted_point_events(
        candidates=sorted_events,
        selected=selected_events,
        limit=omitted_point_event_limit,
    )
    return selected_events, omitted_events


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
              source_quality,
              source_precision
            FROM event_source
            WHERE event_id IN ({placeholders})
            ORDER BY event_id ASC, source_quality ASC, source_precision ASC, id ASC
            """,
            list(event_ids),
        ).fetchall()
    return tuple(_source_from_row(row) for row in rows)
