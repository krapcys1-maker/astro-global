from __future__ import annotations

from scripts.report_curated_source_fragility import (
    _fragility_entry,
    _is_redirect,
    build_fragility_report,
    render_markdown,
)
from services.historical.events import EventSource
from services.historical.source_health import SourceUrlHealth


def _source(source_id: str, url: str, *, quality: str = "encyclopedic") -> EventSource:
    return EventSource(
        id=source_id,
        event_id="evt_one",
        source_type="encyclopedia",
        source_name="Example",
        source_url=url,
        source_quality=quality,
        source_precision="direct",
    )


def test_is_redirect_ignores_trailing_slash_only_changes() -> None:
    assert _is_redirect("https://example.com/path/", "https://example.com/path") is False
    assert _is_redirect("https://example.com/path", "https://example.com/other") is True


def test_fragility_entry_flags_redirect_and_get_fallback() -> None:
    entry = _fragility_entry(
        result=SourceUrlHealth(
            url="https://www.britannica.com/event/source",
            source_ids=("src_one",),
            event_ids=("evt_one",),
            ok=True,
            method="GET",
            status_code=200,
            final_url="https://www.britannica.com/topic/source",
        ),
        metadata={
            "source_qualities": ("encyclopedic",),
            "source_precisions": ("direct",),
            "source_types": ("encyclopedia",),
            "source_names": ("Encyclopaedia Britannica",),
        },
    )

    assert entry["risk_level"] == "high"
    assert entry["flags"] == (
        "head_fallback_required",
        "redirected",
        "encyclopedic_watch",
    )


def test_fragility_report_counts_failures_and_redirects() -> None:
    report = build_fragility_report(
        sources=(
            _source("src_one", "https://example.com/source", quality="institutional"),
            _source("src_two", "https://www.britannica.com/event/source"),
        ),
        results=(
            SourceUrlHealth(
                url="https://example.com/source",
                source_ids=("src_one",),
                event_ids=("evt_one",),
                ok=False,
                method="HEAD",
                status_code=500,
                final_url="https://example.com/source",
                error="HTTP 500",
            ),
            SourceUrlHealth(
                url="https://www.britannica.com/event/source",
                source_ids=("src_two",),
                event_ids=("evt_two",),
                ok=True,
                method="HEAD",
                status_code=200,
                final_url="https://www.britannica.com/topic/source",
            ),
        ),
        include_wikidata=False,
    )

    assert report["failed_count"] == 1
    assert report["redirect_count"] == 1
    assert report["flag_counts"]["http_failure"] == 1
    assert report["flag_counts"]["redirected"] == 1
    assert report["high_risk_count"] == 1
    assert report["medium_risk_count"] == 1


def test_render_markdown_includes_notable_entries() -> None:
    report = build_fragility_report(
        sources=(_source("src_one", "https://example.com/source"),),
        results=(
            SourceUrlHealth(
                url="https://example.com/source",
                source_ids=("src_one",),
                event_ids=("evt_one",),
                ok=False,
                method="HEAD",
                status_code=500,
                final_url="https://example.com/source",
                error="HTTP 500",
            ),
        ),
        include_wikidata=False,
    )

    rendered = render_markdown(report)

    assert "# Curated Source Fragility Report" in rendered
    assert "- Failed: 1" in rendered
    assert "http_failure" in rendered
