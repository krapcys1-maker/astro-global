from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app
from services.historical.curated_importer import load_curated_events, write_events_to_duckdb
from services.resonance.index_builder import BuiltIndex, IndexRow
from services.resonance.index_store import save_built_index
from services.resonance.vectorizer import (
    GLOBAL_SLOW_PROFILE_ID,
    GLOBAL_SLOW_VECTOR_VERSION,
)

SESSION_TOKEN = "deploy-smoke-token"
AUTH_HEADERS = {"x-astro-global-session": SESSION_TOKEN}
DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz"
DEPLOY_CORS_ORIGIN = "https://astro.example"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


@contextmanager
def _temporary_environment(overrides: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _save_sparse_reliable_index(path: Path) -> None:
    datetimes = (
        datetime(1500, 1, 1, tzinfo=UTC),
        datetime(1789, 7, 14, tzinfo=UTC),
        datetime(2026, 5, 23, tzinfo=UTC),
    )
    rows = tuple(
        IndexRow(row_index=index, datetime_utc=dt, julian_day_ut=float(index + 1))
        for index, dt in enumerate(datetimes)
    )
    matrix = np.ones((len(rows), 104), dtype=np.float64)
    save_built_index(
        BuiltIndex(matrix=matrix, rows=rows),
        path,
        profile_id=GLOBAL_SLOW_PROFILE_ID,
        vector_version=GLOBAL_SLOW_VECTOR_VERSION,
        provider="deploy-smoke-synthetic",
        step_days=7,
    )


def _run_smoke() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="astro-global-deploy-smoke-") as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "astro_global.duckdb"
        index_path = tmp_path / DEFAULT_INDEX_FILE
        write_events_to_duckdb(db_path, load_curated_events())
        _save_sparse_reliable_index(index_path)

        with _temporary_environment(
            {
                "ASTRO_GLOBAL_ENV": "production",
                "ASTRO_GLOBAL_SESSION_TOKEN": SESSION_TOKEN,
                "ASTRO_GLOBAL_CORS_ORIGINS": DEPLOY_CORS_ORIGIN,
                "ASTRO_GLOBAL_RATE_LIMIT_ENABLED": "true",
                "ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE": "2",
                "ASTRO_GLOBAL_MAX_REQUEST_BYTES": "64",
            }
        ):
            client = TestClient(
                create_app(
                    event_db_path=db_path,
                    vector_index_root=tmp_path,
                    required_index_file=DEFAULT_INDEX_FILE,
                )
            )

            health = client.get("/health")
            missing_token = client.get("/data/status")
            status = client.get("/data/status", headers=AUTH_HEADERS)
            readiness_missing_token = client.get("/readiness")
            readiness = client.get("/readiness", headers=AUTH_HEADERS)
            too_large = client.post(
                "/sky/at-date",
                headers=AUTH_HEADERS,
                json={
                    "date_utc": "2026-05-23T00:00:00Z",
                    "provider": "synthetic",
                    "padding": "x" * 128,
                },
            )
            rate_headers = AUTH_HEADERS | {"x-forwarded-for": "203.0.113.10"}
            rate_first = client.get("/data/status", headers=rate_headers)
            rate_second = client.get("/data/status", headers=rate_headers)
            rate_limited = client.get("/data/status", headers=rate_headers)

    _assert(health.status_code == 200, f"/health failed: {health.text}")
    _assert(missing_token.status_code == 401, "Protected endpoint accepted missing token.")
    _assert(status.status_code == 200, f"/data/status failed: {status.text}")
    _assert(
        readiness_missing_token.status_code == 401,
        "/readiness accepted missing token.",
    )
    _assert(readiness.status_code == 200, f"/readiness failed: {readiness.text}")
    _assert(too_large.status_code == 413, "Oversized request was not rejected.")
    _assert(rate_first.status_code == 200, "First metered request failed.")
    _assert(rate_second.status_code == 200, "Second metered request failed.")
    _assert(rate_limited.status_code == 429, "Rate limit did not return 429.")

    security = status.json()["security"]
    checks = readiness.json()["checks"]
    _assert(security["runtime_environment"] == "production", "Runtime is not production.")
    _assert(security["cors_allowed_origins"] == [DEPLOY_CORS_ORIGIN], "Unexpected CORS.")
    _assert(security["rate_limit_enabled"] is True, "Rate limit is not enabled.")
    _assert(security["rate_limit_per_minute"] == 2, "Unexpected rate limit.")
    _assert(security["max_request_bytes"] == 64, "Unexpected request size limit.")
    _assert(
        all(check["status"] == "ready" for check in checks),
        f"Readiness checks are not ready: {checks}",
    )

    return {
        "service": status.json()["service"],
        "runtime_environment": security["runtime_environment"],
        "cors_allowed_origins": security["cors_allowed_origins"],
        "rate_limit_per_minute": security["rate_limit_per_minute"],
        "max_request_bytes": security["max_request_bytes"],
        "readiness_status": readiness.json()["status"],
        "readiness_checks": [check["name"] for check in checks],
        "oversized_request_status": too_large.status_code,
        "rate_limited_status": rate_limited.status_code,
    }


def main() -> None:
    result = _run_smoke()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
