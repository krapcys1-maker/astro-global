from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.api.app import create_app

DEFAULT_OUTPUT = ROOT / "contracts" / "openapi_astro_global.json"
REQUIRED_PATHS = {
    "/health",
    "/readiness",
    "/today",
    "/data/status",
    "/sky/current",
    "/sky/at-date",
    "/events/window",
    "/resonance/search",
    "/resonance/compare",
}


def _stable_openapi_schema() -> dict[str, Any]:
    app = create_app(session_token="contract-export-token")
    schema = app.openapi()
    paths = set(schema.get("paths", {}))
    missing_paths = sorted(REQUIRED_PATHS - paths)
    if missing_paths:
        joined = ", ".join(missing_paths)
        raise SystemExit(f"OpenAPI schema is missing required paths: {joined}")
    return schema


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_contract(output_path: Path, *, check: bool) -> None:
    rendered = _stable_json(_stable_openapi_schema())
    if check:
        if not output_path.exists():
            raise SystemExit(f"Missing OpenAPI contract snapshot: {output_path}")
        current = output_path.read_text(encoding="utf-8")
        if current != rendered:
            raise SystemExit(
                f"OpenAPI contract snapshot is stale. Run: python {Path(__file__).as_posix()}"
            )
        print(f"{output_path} is up to date")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote OpenAPI contract snapshot: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    export_contract(args.output, check=args.check)


if __name__ == "__main__":
    main()
