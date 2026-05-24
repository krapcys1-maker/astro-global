from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"

REQUIRED_FILES = (
    WEB_ROOT / "index.html",
    WEB_ROOT / "transparency" / "index.html",
    WEB_ROOT / "styles.css",
    WEB_ROOT / "shell.js",
    WEB_ROOT / "assets" / "horizon.svg",
)
REQUIRED_ROUTES = (
    'data-route="/"',
    'data-route="/today"',
    'data-route="/explorer"',
    'data-route="/compare"',
    'data-route="/calendar"',
    'data-route="/insights"',
    'data-route="/library"',
    'data-route="/blog"',
    'data-route="/contact"',
    'href="./transparency/"',
)
REQUIRED_PRODUCT_TERMS = (
    "Astro Global",
    "Historical Planetary Resonance Explorer",
    "FastAPI",
    "Developer settings",
    "Open Explorer",
    "View Today",
    "Read Transparency",
    "Analyze date",
    "Current Regime",
    "Most similar historical regimes",
    "Historical analogues",
    "What you are seeing",
    "Advanced / technical details",
    "Primary cycles",
    "Confidence",
    "matched events",
    "context events",
    "Why this match",
    "Active cycle windows",
    "Matching resonance window",
    "Peak match",
    "Draft only / human review required",
    "Human-authored astrology notes",
)
REQUIRED_ENDPOINTS = (
    "/health",
    "/data/status",
    "/today",
    "/resonance/search",
    "/resonance/compare",
    "/timeline/seeds",
    "/articles/seeds",
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
    index_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    shell_js = (WEB_ROOT / "shell.js").read_text(encoding="utf-8")
    transparency_html = (WEB_ROOT / "transparency" / "index.html").read_text(
        encoding="utf-8"
    )

    for route in REQUIRED_ROUTES:
        _assert(route in index_html, f"Missing product route in web shell: {route}")
    for required_text in REQUIRED_PRODUCT_TERMS:
        _assert(
            required_text.lower() in web_text.lower(),
            f"Web shell is missing product term: {required_text}",
        )
    for endpoint in REQUIRED_ENDPOINTS:
        _assert(endpoint in shell_js, f"Web shell is missing API endpoint: {endpoint}")
    for forbidden in FORBIDDEN_CLIENT_TERMS:
        _assert(
            forbidden.lower() not in web_text.lower(),
            f"Web shell must not contain backend-only term: {forbidden}",
        )

    _assert('src="./shell.js' in index_html, "index.html does not load shell.js")
    _assert('href="./styles.css' in index_html, "index.html does not load styles.css")
    _assert(
        "__ASTRO_SHELL_READY" in index_html and "__ASTRO_SHELL_READY" in shell_js,
        "Web shell must expose a startup guard instead of failing blank.",
    )
    _assert(
        '<details class="developer-drawer"' in index_html,
        "Developer connection controls must live in a closed drawer.",
    )
    _assert(
        'class="system-bar"' not in index_html,
        "API controls must not be visible as a main-page system bar.",
    )
    _assert("fetch(" in shell_js, "shell.js does not use FastAPI fetch calls.")
    _assert(
        "x-astro-global-session" in shell_js,
        "shell.js does not send the session token header.",
    )
    _assert("setActiveView" in shell_js, "shell.js does not wire view navigation.")
    _assert("renderSearchResult" in shell_js, "shell.js does not render search responses.")
    _assert(
        "contactForm" in shell_js and "privacy-note" in shell_js,
        "Contact shell is missing form state or privacy note.",
    )
    _assert(
        'href="../styles.css"' in transparency_html,
        "Transparency page does not load shared styles.css",
    )
    for required_text in (
        "Swiss Ephemeris",
        "AI is not a planet calculator",
        "reliable layer starts at 1500",
        "Similarity is not prediction",
    ):
        _assert(
            required_text in transparency_html,
            f"Transparency page is missing required text: {required_text}",
        )

    print(
        json.dumps(
            {
                "web_shell": "ok",
                "mode": "thin_api_client",
                "files_checked": [str(path.relative_to(ROOT)) for path in REQUIRED_FILES],
                "required_endpoints": list(REQUIRED_ENDPOINTS),
                "routes": [
                    route.replace('data-route="', "").replace('"', "")
                    for route in REQUIRED_ROUTES
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
