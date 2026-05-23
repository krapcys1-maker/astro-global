from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.historical.events import EventSource

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = "AstroGlobalSourceHealth/0.1 (+https://github.com/krapcys1-maker/astro-global)"
SUCCESS_MIN_STATUS = 200
SUCCESS_MAX_STATUS = 399
HEAD_FALLBACK_STATUSES = {403, 405, 501}


@dataclass(frozen=True)
class SourceUrlGroup:
    url: str
    source_ids: tuple[str, ...]
    event_ids: tuple[str, ...]


@dataclass(frozen=True)
class SourceUrlHealth:
    url: str
    source_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    ok: bool
    method: str
    status_code: int | None = None
    error: str | None = None


OpenUrl = Callable[[Request, float], Any]


def open_url_with_timeout(request: Request, timeout_seconds: float) -> Any:
    return urlopen(request, timeout=timeout_seconds)


def group_source_urls(sources: Sequence[EventSource]) -> tuple[SourceUrlGroup, ...]:
    grouped: dict[str, dict[str, set[str]]] = {}
    for source in sources:
        url = str(source.source_url)
        bucket = grouped.setdefault(url, {"source_ids": set(), "event_ids": set()})
        bucket["source_ids"].add(source.id)
        bucket["event_ids"].add(source.event_id)

    return tuple(
        SourceUrlGroup(
            url=url,
            source_ids=tuple(sorted(values["source_ids"])),
            event_ids=tuple(sorted(values["event_ids"])),
        )
        for url, values in sorted(grouped.items())
    )


def check_source_url_group(
    group: SourceUrlGroup,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    open_url: OpenUrl = open_url_with_timeout,
) -> SourceUrlHealth:
    return _check_url(
        group.url,
        group.source_ids,
        group.event_ids,
        timeout_seconds=timeout_seconds,
        open_url=open_url,
    )


def check_source_url_groups(
    groups: Iterable[SourceUrlGroup],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    open_url: OpenUrl = open_url_with_timeout,
) -> tuple[SourceUrlHealth, ...]:
    return tuple(
        check_source_url_group(
            group,
            timeout_seconds=timeout_seconds,
            open_url=open_url,
        )
        for group in groups
    )


def _check_url(
    url: str,
    source_ids: tuple[str, ...],
    event_ids: tuple[str, ...],
    *,
    timeout_seconds: float,
    open_url: OpenUrl,
) -> SourceUrlHealth:
    head_result = _request_url(url, "HEAD", timeout_seconds=timeout_seconds, open_url=open_url)
    if head_result.ok:
        return SourceUrlHealth(
            url=url,
            source_ids=source_ids,
            event_ids=event_ids,
            ok=True,
            method="HEAD",
            status_code=head_result.status_code,
        )

    if head_result.status_code in HEAD_FALLBACK_STATUSES:
        get_result = _request_url(url, "GET", timeout_seconds=timeout_seconds, open_url=open_url)
        return SourceUrlHealth(
            url=url,
            source_ids=source_ids,
            event_ids=event_ids,
            ok=get_result.ok,
            method="GET",
            status_code=get_result.status_code,
            error=get_result.error if not get_result.ok else None,
        )

    return SourceUrlHealth(
        url=url,
        source_ids=source_ids,
        event_ids=event_ids,
        ok=False,
        method="HEAD",
        status_code=head_result.status_code,
        error=head_result.error,
    )


@dataclass(frozen=True)
class _RequestResult:
    ok: bool
    status_code: int | None
    error: str | None


def _request_url(
    url: str,
    method: str,
    *,
    timeout_seconds: float,
    open_url: OpenUrl,
) -> _RequestResult:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if method == "GET":
        headers["Range"] = "bytes=0-0"
    request = Request(url, headers=headers, method=method)
    try:
        with open_url(request, timeout_seconds) as response:
            status_code = _response_status_code(response)
    except HTTPError as exc:
        status_code = int(exc.code)
        return _RequestResult(
            ok=SUCCESS_MIN_STATUS <= status_code <= SUCCESS_MAX_STATUS,
            status_code=status_code,
            error=f"HTTP {status_code}",
        )
    except URLError as exc:
        return _RequestResult(ok=False, status_code=None, error=str(exc.reason))
    except OSError as exc:
        return _RequestResult(ok=False, status_code=None, error=str(exc))

    ok = SUCCESS_MIN_STATUS <= status_code <= SUCCESS_MAX_STATUS
    return _RequestResult(
        ok=ok,
        status_code=status_code,
        error=None if ok else f"HTTP {status_code}",
    )


def _response_status_code(response: Any) -> int:
    if hasattr(response, "status"):
        return int(response.status)
    if hasattr(response, "getcode"):
        return int(response.getcode())
    return 200
