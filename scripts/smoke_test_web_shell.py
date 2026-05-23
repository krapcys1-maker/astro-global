from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"

REQUIRED_FILES = (
    WEB_ROOT / "index.html",
    WEB_ROOT / "styles.css",
    WEB_ROOT / "shell.js",
    WEB_ROOT / "assets" / "horizon.svg",
)
REQUIRED_ENDPOINTS = (
    "/health",
    "/readiness",
    "/data/status",
    "/resonance/search",
)
FORBIDDEN_CLIENT_TERMS = (
    "duckdb",
    "data/vectors",
    "curated_events.csv",
    "curated_event_sources.csv",
    "load_curated_events",
    "build_weekly_index",
    "vectorize_global_slow",
    "exact_search",
    "localStorage",
    "sessionStorage",
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _read_web_text() -> str:
    missing = [path for path in REQUIRED_FILES if not path.exists()]
    _assert(not missing, f"Missing web shell files: {', '.join(str(path) for path in missing)}")
    return "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED_FILES)


def main() -> None:
    web_text = _read_web_text()
    shell_js = (WEB_ROOT / "shell.js").read_text(encoding="utf-8")
    index_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    for endpoint in REQUIRED_ENDPOINTS:
        _assert(endpoint in shell_js, f"Missing endpoint in web shell: {endpoint}")
    for forbidden in FORBIDDEN_CLIENT_TERMS:
        _assert(
            forbidden.lower() not in web_text.lower(),
            f"Web shell must not contain backend-only term: {forbidden}",
        )
    _assert('src="./shell.js"' in index_html, "index.html does not load shell.js")
    _assert('href="./styles.css"' in index_html, "index.html does not load styles.css")
    _assert(
        '"x-astro-global-session"' in shell_js,
        "Web shell does not send the documented session token header.",
    )
    _assert(
        "deterministic_summary" in shell_js,
        "Web shell does not render deterministic_summary from the API response.",
    )
    _assert(
        "context_events" in shell_js and "matched_events" in shell_js,
        "Web shell must keep matched_events and context_events separate.",
    )

    print(
        json.dumps(
            {
                "web_shell": "ok",
                "files_checked": [str(path.relative_to(ROOT)) for path in REQUIRED_FILES],
                "required_endpoints": list(REQUIRED_ENDPOINTS),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
