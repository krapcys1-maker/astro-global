from __future__ import annotations

from pathlib import Path

from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    load_curated_events,
)
from services.historical.events import HistoricalEvent

DEFAULT_DUCKDB_PATH = Path("data/duckdb/astro_global.duckdb")


def _event_from_row(row: tuple[object, ...]) -> HistoricalEvent:
    return HistoricalEvent(
        id=str(row[0]),
        title=str(row[1]),
        display_date=str(row[2]),
        start_astro_year=int(row[3]),
        end_astro_year=int(row[4]),
        category=str(row[5]),
        region=str(row[6]),
        geo_scope=str(row[7]),
        source_url=str(row[8]),
        confidence_score=float(row[9]),
        schema_version=str(row[10]),
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
        return tuple(
            event
            for event in load_curated_events(DEFAULT_CURATED_EVENTS_PATH)
            if event.start_astro_year <= end_astro_year and event.end_astro_year >= start_astro_year
        )[:limit]

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
              region,
              geo_scope,
              source_url,
              confidence_score,
              schema_version
            FROM historical_event
            WHERE start_astro_year <= ?
              AND end_astro_year >= ?
            ORDER BY confidence_score DESC, start_astro_year ASC, id ASC
            LIMIT ?
            """,
            [end_astro_year, start_astro_year, limit],
        ).fetchall()
    return tuple(_event_from_row(row) for row in rows)
