from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from services.ephemeris.provider import EphemerisProvider
from services.resonance.vectorizer import vectorize_global_slow


@dataclass(frozen=True)
class IndexRow:
    row_index: int
    datetime_utc: datetime
    julian_day_ut: float


@dataclass(frozen=True)
class BuiltIndex:
    matrix: np.ndarray
    rows: tuple[IndexRow, ...]


def build_weekly_index(
    provider: EphemerisProvider,
    start_utc: datetime,
    end_utc: datetime,
    step_days: int = 7,
) -> BuiltIndex:
    vectors: list[np.ndarray] = []
    rows: list[IndexRow] = []
    current = start_utc
    row_index = 0
    while current <= end_utc:
        state = provider.compute_state(current)
        vectorized = vectorize_global_slow(state)
        vectors.append(vectorized.vector)
        rows.append(
            IndexRow(row_index=row_index, datetime_utc=current, julian_day_ut=state.julian_day_ut)
        )
        row_index += 1
        current += timedelta(days=step_days)
    matrix = np.vstack(vectors) if vectors else np.empty((0, 0), dtype=np.float64)
    return BuiltIndex(matrix=matrix, rows=tuple(rows))
