from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.historical.curated_importer import (
    DEFAULT_CURATED_EVENTS_PATH,
    event_sources_from_events,
    load_curated_events,
)
from services.historical.events import EventSource
from services.historical.source_health import (
    DEFAULT_TIMEOUT_SECONDS,
    SourceUrlHealth,
    check_source_url_group,
    group_source_urls,
)

DEFAULT_JSON_OUTPUT = ROOT / "work" / "reports" / "curated_source_fragility.json"
DEFAULT_MD_OUTPUT = ROOT / "work" / "reports" / "curated_source_fragility.md"
ENCYCLOPEDIC_FLAG_DOMAINS = ("britannica.com",)
INSTITUTIONAL_WATCH_QUALITIES = frozenset({"institutional"})
CONTEXTUAL_PRECISIONS = frozenset({"contextual", "broad_context"})


def build_fragility_report(
    *,
    sources: tuple[EventSource, ...],
    results: tuple[SourceUrlHealth, ...],
    include_wikidata: bool,
) -> dict[str, Any]:
    metadata_by_url = _source_metadata_by_url(sources)
    entries = tuple(
        _fragility_entry(
            result=result,
            metadata=metadata_by_url.get(result.url, {}),
        )
        for result in results
    )
    flag_counts = Counter(flag for entry in entries for flag in entry["flags"])
    domain_counts = Counter(entry["domain"] for entry in entries)
    high_risk_entries = tuple(entry for entry in entries if entry["risk_level"] == "high")
    medium_risk_entries = tuple(entry for entry in entries if entry["risk_level"] == "medium")
    return {
        "include_wikidata": include_wikidata,
        "sources_loaded": len(sources),
        "unique_urls_checked": len(results),
        "ok_count": sum(1 for result in results if result.ok),
        "failed_count": sum(1 for result in results if not result.ok),
        "redirect_count": sum(1 for entry in entries if "redirected" in entry["flags"]),
        "head_fallback_count": sum(
            1 for entry in entries if "head_fallback_required" in entry["flags"]
        ),
        "high_risk_count": len(high_risk_entries),
        "medium_risk_count": len(medium_risk_entries),
        "flag_counts": dict(sorted(flag_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "entries": sorted(
            entries,
            key=lambda entry: (
                -int(entry["risk_score"]),
                entry["domain"],
                entry["url"],
            ),
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Curated Source Fragility Report",
        "",
        f"- Sources loaded: {report['sources_loaded']}",
        f"- Unique URLs checked: {report['unique_urls_checked']}",
        f"- OK: {report['ok_count']}",
        f"- Failed: {report['failed_count']}",
        f"- Redirects: {report['redirect_count']}",
        f"- HEAD fallbacks: {report['head_fallback_count']}",
        f"- High risk: {report['high_risk_count']}",
        f"- Medium risk: {report['medium_risk_count']}",
        f"- Flag counts: `{json.dumps(report['flag_counts'], sort_keys=True)}`",
        "",
        "## High And Medium Risk URLs",
        "",
    ]
    notable_entries = [
        entry for entry in report["entries"] if entry["risk_level"] in {"high", "medium"}
    ]
    if not notable_entries:
        lines.append("- none")
    for entry in notable_entries:
        lines.extend(_render_entry(entry))
    lines.extend(["", "## Domain Counts", ""])
    for domain, count in report["domain_counts"].items():
        lines.append(f"- `{domain}`: {count}")
    return "\n".join(lines).rstrip() + "\n"


def _render_entry(entry: dict[str, Any]) -> list[str]:
    final_url_note = ""
    if entry["final_url"] and entry["final_url"] != entry["url"]:
        final_url_note = f" -> {entry['final_url']}"
    return [
        f"### {entry['domain']}",
        "",
        f"- URL: `{entry['url']}{final_url_note}`",
        f"- Risk: `{entry['risk_level']}` ({entry['risk_score']})",
        f"- Flags: `{', '.join(entry['flags']) or 'none'}`",
        f"- Method/status: `{entry['method']} {entry['status_code']}`",
        f"- Event IDs: `{', '.join(entry['event_ids'])}`",
        f"- Source IDs: `{', '.join(entry['source_ids'])}`",
        "",
    ]


def _fragility_entry(
    *,
    result: SourceUrlHealth,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    domain = _domain(result.url)
    flags = _fragility_flags(result=result, metadata=metadata, domain=domain)
    risk_score = _risk_score(flags)
    return {
        "url": result.url,
        "final_url": result.final_url,
        "domain": domain,
        "ok": result.ok,
        "method": result.method,
        "status_code": result.status_code,
        "error": result.error,
        "source_ids": result.source_ids,
        "event_ids": result.event_ids,
        "source_qualities": metadata.get("source_qualities", ()),
        "source_precisions": metadata.get("source_precisions", ()),
        "source_types": metadata.get("source_types", ()),
        "source_names": metadata.get("source_names", ()),
        "flags": flags,
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
    }


def _fragility_flags(
    *,
    result: SourceUrlHealth,
    metadata: dict[str, Any],
    domain: str,
) -> tuple[str, ...]:
    flags: list[str] = []
    qualities = set(metadata.get("source_qualities", ()))
    precisions = set(metadata.get("source_precisions", ()))
    if not result.ok:
        flags.append("http_failure")
    if result.method == "GET":
        flags.append("head_fallback_required")
    if _is_redirect(result.url, result.final_url):
        flags.append("redirected")
    if urlparse(result.url).scheme != "https":
        flags.append("non_https")
    if qualities & INSTITUTIONAL_WATCH_QUALITIES:
        flags.append("institutional_watch")
    if any(domain.endswith(flagged_domain) for flagged_domain in ENCYCLOPEDIC_FLAG_DOMAINS):
        flags.append("encyclopedic_watch")
    if precisions & CONTEXTUAL_PRECISIONS:
        flags.append("weak_precision")
    return tuple(flags)


def _risk_score(flags: tuple[str, ...]) -> int:
    weights = {
        "http_failure": 100,
        "head_fallback_required": 70,
        "redirected": 35,
        "non_https": 30,
        "weak_precision": 25,
        "institutional_watch": 10,
        "encyclopedic_watch": 10,
    }
    return sum(weights.get(flag, 0) for flag in flags)


def _risk_level(risk_score: int) -> str:
    if risk_score >= 80:
        return "high"
    if risk_score >= 35:
        return "medium"
    if risk_score > 0:
        return "low"
    return "none"


def _is_redirect(url: str, final_url: str | None) -> bool:
    if not final_url:
        return False
    return _normalize_url(url) != _normalize_url(final_url)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _source_metadata_by_url(
    sources: tuple[EventSource, ...],
) -> dict[str, dict[str, tuple[str, ...]]]:
    grouped: dict[str, dict[str, set[str]]] = {}
    for source in sources:
        bucket = grouped.setdefault(
            str(source.source_url),
            {
                "source_qualities": set(),
                "source_precisions": set(),
                "source_types": set(),
                "source_names": set(),
            },
        )
        bucket["source_qualities"].add(source.source_quality)
        bucket["source_precisions"].add(source.source_precision)
        bucket["source_types"].add(source.source_type)
        bucket["source_names"].add(source.source_name)
    return {
        url: {
            key: tuple(sorted(values))
            for key, values in metadata.items()
        }
        for url, metadata in grouped.items()
    }


def _load_sources(events_csv: Path, include_wikidata: bool) -> tuple[EventSource, ...]:
    events = load_curated_events(events_csv)
    all_sources = event_sources_from_events(events)
    if include_wikidata:
        return all_sources
    return tuple(source for source in all_sources if source.source_quality != "wikidata_seed")


def _check_sources(
    *,
    sources: tuple[EventSource, ...],
    timeout_seconds: float,
    workers: int,
    limit: int | None,
) -> tuple[SourceUrlHealth, ...]:
    groups = group_source_urls(sources)
    if limit is not None:
        groups = groups[:limit]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return tuple(
            executor.map(
                lambda group: check_source_url_group(
                    group,
                    timeout_seconds=timeout_seconds,
                ),
                groups,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report fragility signals for curated historical source URLs."
    )
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_CURATED_EVENTS_PATH)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-wikidata", action="store_true")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    sources = _load_sources(args.events_csv, args.include_wikidata)
    results = _check_sources(
        sources=sources,
        timeout_seconds=args.timeout,
        workers=args.workers,
        limit=args.limit,
    )
    report = build_fragility_report(
        sources=sources,
        results=results,
        include_wikidata=args.include_wikidata,
    )
    rendered_json = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    rendered_md = render_markdown(report)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(rendered_json, encoding="utf-8")
    args.md_output.write_text(rendered_md, encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "sources_loaded": report["sources_loaded"],
                "unique_urls_checked": report["unique_urls_checked"],
                "failed_count": report["failed_count"],
                "redirect_count": report["redirect_count"],
                "head_fallback_count": report["head_fallback_count"],
                "high_risk_count": report["high_risk_count"],
                "medium_risk_count": report["medium_risk_count"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if report["failed_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
