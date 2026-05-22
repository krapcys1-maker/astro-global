from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from services.resonance.index_builder import BuiltIndex, IndexRow

INDEX_STORE_VERSION = "planetary_index_npz_v1"


def save_built_index(
    built_index: BuiltIndex,
    output_path: Path | str,
    *,
    profile_id: str,
    vector_version: str,
    provider: str,
    step_days: int,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "store_version": INDEX_STORE_VERSION,
        "profile_id": profile_id,
        "vector_version": vector_version,
        "provider": provider,
        "step_days": step_days,
        "rows": [
            {
                "row_index": row.row_index,
                "datetime_utc": row.datetime_utc.isoformat(),
                "julian_day_ut": row.julian_day_ut,
            }
            for row in built_index.rows
        ],
    }
    np.savez_compressed(
        path,
        matrix=built_index.matrix,
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
    )


def load_built_index(input_path: Path | str) -> tuple[BuiltIndex, dict[str, Any]]:
    path = Path(input_path)
    with np.load(path, allow_pickle=False) as payload:
        matrix = np.asarray(payload["matrix"], dtype=np.float64)
        metadata = json.loads(str(payload["metadata_json"]))
    if metadata.get("store_version") != INDEX_STORE_VERSION:
        msg = f"Unsupported index store version: {metadata.get('store_version')}"
        raise ValueError(msg)
    rows = tuple(
        IndexRow(
            row_index=int(row["row_index"]),
            datetime_utc=datetime.fromisoformat(str(row["datetime_utc"])),
            julian_day_ut=float(row["julian_day_ut"]),
        )
        for row in metadata["rows"]
    )
    return BuiltIndex(matrix=matrix, rows=rows), metadata
