from __future__ import annotations

import csv
from pathlib import Path

from services.historical.events import HistoricalEvent

DEFAULT_CURATED_EVENTS_PATH = Path(__file__).parent / "seeds" / "curated_events.csv"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def load_curated_events(
    path: Path | str = DEFAULT_CURATED_EVENTS_PATH,
) -> tuple[HistoricalEvent, ...]:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        events = [HistoricalEvent.model_validate(row) for row in reader]
    ids = [event.id for event in events]
    if len(ids) != len(set(ids)):
        msg = "curated events contain duplicate ids"
        raise ValueError(msg)
    return tuple(events)


def initialize_duckdb(db_path: Path | str) -> None:
    try:
        import duckdb
    except ModuleNotFoundError as exc:
        msg = "DuckDB support requires the project dependency 'duckdb'."
        raise RuntimeError(msg) from exc

    with duckdb.connect(str(db_path)) as connection:
        connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def write_events_to_duckdb(
    db_path: Path | str,
    events: tuple[HistoricalEvent, ...],
    replace: bool = True,
) -> None:
    try:
        import duckdb
    except ModuleNotFoundError as exc:
        msg = "DuckDB support requires the project dependency 'duckdb'."
        raise RuntimeError(msg) from exc

    initialize_duckdb(db_path)
    with duckdb.connect(str(db_path)) as connection:
        if replace:
            connection.execute("DELETE FROM historical_event")
        rows = [
            (
                event.id,
                event.title,
                event.display_date,
                event.start_astro_year,
                event.end_astro_year,
                event.category,
                event.region,
                event.geo_scope,
                str(event.source_url),
                event.confidence_score,
                event.schema_version,
            )
            for event in events
        ]
        connection.executemany(
            """
            INSERT INTO historical_event (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
