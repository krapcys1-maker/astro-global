from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request

from services.historical.events import EventSource
from services.historical.source_health import (
    SourceUrlGroup,
    check_source_url_group,
    group_source_urls,
)


class FakeResponse:
    def __init__(self, status: int, *, final_url: str | None = None) -> None:
        self.status = status
        self._final_url = final_url

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def geturl(self) -> str:
        return self._final_url or "https://example.com/source"


def test_group_source_urls_deduplicates_sources_and_events() -> None:
    sources = (
        EventSource(
            id="src_a",
            event_id="evt_one",
            source_type="encyclopedia",
            source_name="Example",
            source_url="https://example.com/source",
            source_quality="encyclopedic",
        ),
        EventSource(
            id="src_b",
            event_id="evt_two",
            source_type="encyclopedia",
            source_name="Example",
            source_url="https://example.com/source",
            source_quality="encyclopedic",
        ),
    )

    groups = group_source_urls(sources)

    assert groups == (
        SourceUrlGroup(
            url="https://example.com/source",
            source_ids=("src_a", "src_b"),
            event_ids=("evt_one", "evt_two"),
        ),
    )


def test_check_source_url_group_accepts_successful_head() -> None:
    seen_methods: list[str] = []

    def open_url(request: Request, timeout_seconds: float) -> FakeResponse:
        seen_methods.append(request.get_method())
        assert timeout_seconds == 2.0
        return FakeResponse(204)

    result = check_source_url_group(
        SourceUrlGroup(
            url="https://example.com/source",
            source_ids=("src_a",),
            event_ids=("evt_one",),
        ),
        timeout_seconds=2.0,
        open_url=open_url,
    )

    assert result.ok is True
    assert result.method == "HEAD"
    assert result.status_code == 204
    assert result.final_url == "https://example.com/source"
    assert seen_methods == ["HEAD"]


def test_check_source_url_group_reports_final_url_after_redirect() -> None:
    def open_url(request: Request, timeout_seconds: float) -> FakeResponse:
        return FakeResponse(200, final_url="https://example.com/final")

    result = check_source_url_group(
        SourceUrlGroup(
            url="https://example.com/source",
            source_ids=("src_a",),
            event_ids=("evt_one",),
        ),
        open_url=open_url,
    )

    assert result.ok is True
    assert result.final_url == "https://example.com/final"


def test_check_source_url_group_falls_back_to_get_for_head_block() -> None:
    seen_methods: list[str] = []

    def open_url(request: Request, timeout_seconds: float) -> FakeResponse:
        seen_methods.append(request.get_method())
        if request.get_method() == "HEAD":
            raise HTTPError(request.full_url, 405, "Method Not Allowed", hdrs=None, fp=None)
        assert request.headers["Range"] == "bytes=0-0"
        return FakeResponse(200)

    result = check_source_url_group(
        SourceUrlGroup(
            url="https://example.com/source",
            source_ids=("src_a",),
            event_ids=("evt_one",),
        ),
        open_url=open_url,
    )

    assert result.ok is True
    assert result.method == "GET"
    assert result.status_code == 200
    assert seen_methods == ["HEAD", "GET"]


def test_check_source_url_group_reports_network_errors() -> None:
    def open_url(request: Request, timeout_seconds: float) -> FakeResponse:
        raise URLError("connection refused")

    result = check_source_url_group(
        SourceUrlGroup(
            url="https://example.com/source",
            source_ids=("src_a",),
            event_ids=("evt_one",),
        ),
        open_url=open_url,
    )

    assert result.ok is False
    assert result.method == "HEAD"
    assert result.status_code is None
    assert "connection refused" in str(result.error)
