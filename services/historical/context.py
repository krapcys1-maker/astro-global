from __future__ import annotations

BROAD_CONTEXT_EVENT_IDS = frozenset(
    {
        "evt_enlightenment",
        "evt_urbanization_acceleration",
        "evt_neoliberal_turn",
        "evt_globalization_era",
        "evt_belt_and_road_initiative",
    }
)


def is_broad_context_event_id(event_id: str) -> bool:
    return event_id in BROAD_CONTEXT_EVENT_IDS
