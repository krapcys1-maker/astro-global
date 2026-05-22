from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict

from services.historical.events import HistoricalEvent


class EventCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    events_found: int
    regions: dict[str, int]
    categories: dict[str, int]
    event_kinds: dict[str, int]
    ongoing_events_count: int
    dominant_region_bias: str | None
    warning: str | None


def build_coverage_report(events: tuple[HistoricalEvent, ...]) -> EventCoverageReport:
    regions = Counter(event.region for event in events)
    categories = Counter(event.category for event in events)
    event_kinds = Counter(event.event_kind for event in events)
    dominant_region = regions.most_common(1)[0][0] if regions else None
    warning = None
    if not events:
        warning = "No historical events found for this period."
    elif dominant_region and regions[dominant_region] / len(events) >= 0.6:
        warning = "Historical source coverage is uneven for this period."
    return EventCoverageReport(
        events_found=len(events),
        regions=dict(regions),
        categories=dict(categories),
        event_kinds=dict(event_kinds),
        ongoing_events_count=sum(1 for event in events if event.is_ongoing),
        dominant_region_bias=dominant_region,
        warning=warning,
    )
