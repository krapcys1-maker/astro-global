from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from services.historical.events import EventSource, HistoricalEvent

DOMINANT_CATEGORY_THRESHOLD = 0.35
DOMINANT_EVENT_KIND_THRESHOLD = 0.35
MIN_PRIMARY_OR_INSTITUTIONAL_SOURCE_SHARE = 0.10


class DataBiasBucket(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    count: int
    share: float


class HistoricalDataBiasReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    events_count: int
    sources_count: int
    start_astro_year_min: int | None
    end_astro_year_max: int | None
    ongoing_events_count: int
    categories: tuple[DataBiasBucket, ...]
    event_kinds: tuple[DataBiasBucket, ...]
    regions: tuple[DataBiasBucket, ...]
    source_quality: tuple[DataBiasBucket, ...]
    source_precision: tuple[DataBiasBucket, ...]
    warnings: tuple[str, ...]


def _distribution(values: Sequence[str], *, total: int | None = None) -> tuple[DataBiasBucket, ...]:
    denominator = total if total is not None else len(values)
    counts = Counter(values)
    return tuple(
        DataBiasBucket(
            label=label,
            count=count,
            share=count / denominator if denominator else 0.0,
        )
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )


def _top_bucket(buckets: tuple[DataBiasBucket, ...]) -> DataBiasBucket | None:
    return buckets[0] if buckets else None


def build_historical_data_bias_report(
    *,
    events: Sequence[HistoricalEvent],
    sources: Sequence[EventSource],
) -> HistoricalDataBiasReport:
    events_tuple = tuple(events)
    sources_tuple = tuple(sources)
    categories = _distribution([event.category for event in events_tuple])
    event_kinds = _distribution([event.event_kind for event in events_tuple])
    regions = _distribution([event.region for event in events_tuple])
    source_quality = _distribution([source.source_quality for source in sources_tuple])
    source_precision = _distribution([source.source_precision for source in sources_tuple])

    warnings: list[str] = []
    top_category = _top_bucket(categories)
    if top_category and top_category.share >= DOMINANT_CATEGORY_THRESHOLD:
        warnings.append(
            "Dominant category bias: "
            f"{top_category.label} is {top_category.share:.1%} of curated events."
        )
    top_event_kind = _top_bucket(event_kinds)
    if top_event_kind and top_event_kind.share >= DOMINANT_EVENT_KIND_THRESHOLD:
        warnings.append(
            "Dominant event kind bias: "
            f"{top_event_kind.label} is {top_event_kind.share:.1%} of curated events."
        )
    source_quality_counts = Counter(source.source_quality for source in sources_tuple)
    primary_or_institutional = (
        source_quality_counts["primary"] + source_quality_counts["institutional"]
    )
    source_share = primary_or_institutional / len(sources_tuple) if sources_tuple else 0.0
    if source_share < MIN_PRIMARY_OR_INSTITUTIONAL_SOURCE_SHARE:
        warnings.append(
            "Primary/institutional source share is low: "
            f"{source_share:.1%} of all generated and curated sources."
        )

    return HistoricalDataBiasReport(
        events_count=len(events_tuple),
        sources_count=len(sources_tuple),
        start_astro_year_min=(
            min(event.start_astro_year for event in events_tuple) if events_tuple else None
        ),
        end_astro_year_max=(
            max(event.end_astro_year for event in events_tuple) if events_tuple else None
        ),
        ongoing_events_count=sum(1 for event in events_tuple if event.is_ongoing),
        categories=categories,
        event_kinds=event_kinds,
        regions=regions,
        source_quality=source_quality,
        source_precision=source_precision,
        warnings=tuple(warnings),
    )


def render_historical_data_bias_markdown(report: HistoricalDataBiasReport) -> str:
    lines = [
        "# Raport biasu danych historycznych - Astro Global",
        "",
        "## Podsumowanie",
        "",
        f"- Eventy: {report.events_count}",
        f"- Zrodla lacznie: {report.sources_count}",
        f"- Zakres lat: {report.start_astro_year_min}-{report.end_astro_year_max}",
        f"- Eventy trwajace: {report.ongoing_events_count}",
        "",
        "## Ostrzezenia",
        "",
    ]
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- Brak ostrzezen biasu wedlug aktualnych progow.")
    lines.extend(
        [
            "",
            _render_distribution("Kategorie", report.categories),
            "",
            _render_distribution("Typy eventow", report.event_kinds),
            "",
            _render_distribution("Regiony", report.regions),
            "",
            _render_distribution("Jakosc zrodel", report.source_quality),
            "",
            _render_distribution("Precyzja zrodel", report.source_precision),
        ]
    )
    return "\n".join(lines)


def _render_distribution(title: str, buckets: tuple[DataBiasBucket, ...]) -> str:
    lines = [f"## {title}", "", "| Pozycja | Liczba | Udzial |", "| --- | ---: | ---: |"]
    lines.extend(
        f"| {bucket.label} | {bucket.count} | {bucket.share:.1%} |" for bucket in buckets
    )
    return "\n".join(lines)
