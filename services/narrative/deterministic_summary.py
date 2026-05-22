from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

NON_PREDICTIVE_GUARDRAIL = "To jest opis podobieństwa symboliczno-historycznego, nie prognoza."


class DeterministicSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str = "pl"
    summary: str
    key_points: tuple[str, ...]
    referenced_event_ids: tuple[str, ...]
    guardrails: tuple[str, ...]


def _cycle_label(cycle: dict[str, Any]) -> str:
    pair = cycle.get("pair", ())
    if isinstance(pair, list | tuple) and len(pair) == 2:
        pair_label = f"{pair[0]}-{pair[1]}"
    else:
        pair_label = "nieznana para"
    aspect = str(cycle.get("aspect", "nieznany aspekt"))
    tier = str(cycle.get("tier", "bez tieru"))
    contribution = float(cycle.get("contribution", 0.0))
    return f"{pair_label}: {aspect}, {tier}, wkład {contribution:.3f}"


def _event_id(event: Any) -> str:
    return str(getattr(event, "event_id", ""))


def _event_title(event: Any) -> str:
    return str(getattr(event, "title", ""))


def build_deterministic_summary(
    *,
    profile_id: str,
    query_datetime_utc: str,
    primary_cycles: Sequence[dict[str, Any]],
    supporting_cycles: Sequence[dict[str, Any]],
    episodes: Sequence[Any],
) -> DeterministicSummary:
    strongest_episode = episodes[0] if episodes else None
    cycle_labels = [_cycle_label(cycle) for cycle in primary_cycles[:3]]
    if not cycle_labels:
        cycle_labels = [_cycle_label(cycle) for cycle in supporting_cycles[:3]]

    referenced_event_ids: list[str] = []
    event_labels: list[str] = []
    if strongest_episode is not None:
        for event in strongest_episode.matched_events[:3]:
            event_id = _event_id(event)
            if event_id:
                referenced_event_ids.append(event_id)
            title = _event_title(event)
            if event_id and title:
                event_labels.append(f"{title} ({event_id})")
            elif title:
                event_labels.append(title)

    if strongest_episode is None:
        summary = (
            f"Dla daty {query_datetime_utc} profil {profile_id} nie zwrócił niezależnych "
            "epizodów rezonansu w badanym zakresie. "
            f"{NON_PREDICTIVE_GUARDRAIL}"
        )
        return DeterministicSummary(
            summary=summary,
            key_points=("Brak epizodów do opisania.",),
            referenced_event_ids=(),
            guardrails=(NON_PREDICTIVE_GUARDRAIL,),
        )

    event_sentence = (
        "Najbliższy kontekst historyczny: " + "; ".join(event_labels) + "."
        if event_labels
        else "Brak wydarzeń historycznych w kontrolowanej bazie dla tego okna."
    )
    cycle_sentence = (
        "Najważniejsze cykle: " + "; ".join(cycle_labels) + "."
        if cycle_labels
        else "W odpowiedzi nie ma silnych cykli do wyróżnienia."
    )
    summary = (
        f"Dla daty {query_datetime_utc} profil {profile_id} znalazł "
        f"{len(episodes)} niezależnych epizodów podobieństwa. "
        f"Najsilniejszy epizod skupia się wokół {strongest_episode.best_date}, "
        f"z wynikiem {strongest_episode.best_score:.3f} i percentylem "
        f"{strongest_episode.best_percentile:.3f}. "
        f"{cycle_sentence} {event_sentence} {NON_PREDICTIVE_GUARDRAIL}"
    )
    key_points = (
        f"Najsilniejszy epizod: {strongest_episode.best_date}.",
        cycle_sentence,
        event_sentence,
    )
    return DeterministicSummary(
        summary=summary,
        key_points=key_points,
        referenced_event_ids=tuple(referenced_event_ids),
        guardrails=(NON_PREDICTIVE_GUARDRAIL,),
    )
