from __future__ import annotations

import argparse
import json
import ssl
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.astro_rules.angles import angular_distance_deg

BODY_COMMANDS = {
    "Sun": "10",
    "Moon": "301",
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
    "Uranus": "799",
    "Neptune": "899",
    "Pluto": "999",
}

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
DEFAULT_OUTPUT = ROOT / "tests" / "golden" / "planetary_states" / "jpl_horizons_2026-05-22T12Z.json"


def parse_utc_minute(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(second=0, microsecond=0)


def horizons_time(value: datetime) -> str:
    return value.strftime("%Y-%b-%d %H:%M")


def fetch_horizons_rows(
    *,
    body_command: str,
    dt_utc: datetime,
    allow_insecure_ssl: bool,
) -> list[dict[str, float | str]]:
    stop_utc = dt_utc + timedelta(minutes=1)
    params = {
        "format": "text",
        "COMMAND": body_command,
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "500@399",
        "START_TIME": f"'{horizons_time(dt_utc)}'",
        "STOP_TIME": f"'{horizons_time(stop_utc)}'",
        "STEP_SIZE": "'1 m'",
        "QUANTITIES": "31",
        "CSV_FORMAT": "YES",
        "CAL_FORMAT": "CAL",
        "TIME_DIGITS": "MINUTES",
    }
    context = ssl._create_unverified_context() if allow_insecure_ssl else None
    with urlopen(
        f"{HORIZONS_API_URL}?{urlencode(params)}",
        timeout=30,
        context=context,
    ) as response:
        text = response.read().decode("utf-8")

    start = text.index("$$SOE") + len("$$SOE")
    end = text.index("$$EOE")
    rows: list[dict[str, float | str]] = []
    for raw_line in text[start:end].strip().splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) < 5:
            continue
        rows.append(
            {
                "datetime_utc": parts[0],
                "longitude_deg": float(parts[3]),
                "latitude_deg": float(parts[4]),
            }
        )
    if len(rows) != 2:
        msg = f"Horizons returned {len(rows)} rows for body command {body_command}; expected 2."
        raise RuntimeError(msg)
    return rows


def signed_delta_deg(start: float, end: float) -> float:
    unsigned = angular_distance_deg(start, end)
    raw = (end - start) % 360.0
    return -unsigned if raw > 180.0 else unsigned


def build_fixture(dt_utc: datetime, allow_insecure_ssl: bool) -> dict[str, object]:
    positions: list[dict[str, object]] = []
    for body, command in BODY_COMMANDS.items():
        rows = fetch_horizons_rows(
            body_command=command,
            dt_utc=dt_utc,
            allow_insecure_ssl=allow_insecure_ssl,
        )
        current, next_minute = rows
        speed = (
            signed_delta_deg(
                float(current["longitude_deg"]),
                float(next_minute["longitude_deg"]),
            )
            * 1440.0
        )
        positions.append(
            {
                "body": body,
                "horizons_command": command,
                "longitude_deg": round(float(current["longitude_deg"]), 7),
                "latitude_deg": round(float(current["latitude_deg"]), 7),
                "speed_longitude_deg_per_day": round(speed, 7),
            }
        )

    return {
        "schema_version": 1,
        "source": "NASA/JPL Horizons API",
        "source_url": HORIZONS_API_URL,
        "oracle": "JPL DE441 observer-centered ecliptic-of-date apparent coordinates",
        "center": "500@399",
        "quantities": "31",
        "datetime_utc": dt_utc.isoformat().replace("+00:00", "Z"),
        "tolerances": {
            "longitude_deg": 0.25,
            "latitude_deg": 0.25,
            "speed_longitude_deg_per_day": 0.20,
        },
        "positions": positions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch JPL Horizons planetary goldens for ephemeris regression tests."
    )
    parser.add_argument("--date", default="2026-05-22T12:00:00Z")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-insecure-ssl",
        action="store_true",
        help="Allow local SSL interception while fetching NASA/JPL Horizons data.",
    )
    args = parser.parse_args()

    fixture = build_fixture(parse_utc_minute(args.date), args.allow_insecure_ssl)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
