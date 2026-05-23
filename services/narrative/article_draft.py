from __future__ import annotations

import re
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict

from services.api.schemas import (
    ArticleSeedResponse,
    EventSourceResponse,
    HistoricalEventResponse,
    ResonanceCompareResponse,
    ResonanceEpisodeResponse,
)

ARTICLE_DRAFT_CONTENT_POLICY = "backend_facts_only_no_prediction"
ARTICLE_DRAFT_EDITORIAL_STATUS = "draft_needs_human_review"
ARTICLE_FACT_PACK_POLICY = "backend_fact_pack_no_generated_text"

FORBIDDEN_DRAFT_PHRASES = (
    "na pewno",
    "pewne jest",
    "przewidujemy",
    "to sie wydarzy",
    "wydarzy sie",
    "planety spowoduja",
    "planety powodują",
    "planety spowodują",
)
EVENT_ID_PATTERN = re.compile(r"\bevt_[a-zA-Z0-9_]+\b")
SOURCE_ID_PATTERN = re.compile(r"\bsrc_[a-zA-Z0-9_]+\b")


class ArticleSourceFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    event_id: str
    source_type: str
    source_name: str
    source_url: str
    source_quality: str
    source_precision: str


class ArticleEventFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    event_kind: str
    is_ongoing: bool
    end_year_policy: str
    region: str
    geo_scope: str
    confidence_score: float
    roles: tuple[str, ...]
    source_ids: tuple[str, ...]


class ArticleEpisodeFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    side: Literal["left", "right"]
    period_start: str
    period_end: str
    best_date: str
    score_label: str
    narrative_confidence: float
    matched_event_ids: tuple[str, ...]
    context_event_ids: tuple[str, ...]
    warnings: tuple[str, ...]


class ArticleDraftFactPack(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed_id: str
    title: str
    summary: str
    compare_preset_id: str
    source_event_ids: tuple[str, ...]
    source_event_titles: tuple[str, ...]
    content_policy: str = ARTICLE_FACT_PACK_POLICY
    output_policy: str = ARTICLE_DRAFT_CONTENT_POLICY
    editorial_status_required: str = ARTICLE_DRAFT_EDITORIAL_STATUS
    compare_summary: str
    query_vector_similarity: float
    shared_primary_cycles: tuple[str, ...]
    shared_matched_event_ids: tuple[str, ...]
    shared_context_event_ids: tuple[str, ...]
    allowed_event_ids: tuple[str, ...]
    allowed_source_ids: tuple[str, ...]
    events: tuple[ArticleEventFact, ...]
    sources: tuple[ArticleSourceFact, ...]
    episodes: tuple[ArticleEpisodeFact, ...]
    warnings: tuple[str, ...]
    writing_constraints: tuple[str, ...]


class ArticleDraftClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    text: str
    event_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    cycle_labels: tuple[str, ...] = ()


class ArticleDraftSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    section_id: str
    heading: str
    paragraphs: tuple[str, ...]
    claims: tuple[ArticleDraftClaim, ...] = ()


class ArticleDraftOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed_id: str
    title: str
    language: str = "pl"
    content_policy: str = ARTICLE_DRAFT_CONTENT_POLICY
    editorial_status: str = ARTICLE_DRAFT_EDITORIAL_STATUS
    sections: tuple[ArticleDraftSection, ...]
    used_event_ids: tuple[str, ...]
    used_source_ids: tuple[str, ...]
    warnings: tuple[str, ...]


class ArticleDraftValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def build_article_draft_fact_pack(
    *,
    seed: ArticleSeedResponse,
    compare: ResonanceCompareResponse,
) -> ArticleDraftFactPack:
    events_by_id: dict[str, HistoricalEventResponse] = {}
    roles_by_event_id: dict[str, set[str]] = defaultdict(set)
    sources_by_id: dict[str, ArticleSourceFact] = {}
    episodes: list[ArticleEpisodeFact] = []

    for side, search in (("left", compare.left), ("right", compare.right)):
        for episode_index, episode in enumerate(search.episodes, start=1):
            matched_ids = _collect_episode_events(
                events=episode.matched_events,
                events_by_id=events_by_id,
                roles_by_event_id=roles_by_event_id,
                sources_by_id=sources_by_id,
                role=f"{side}_matched",
            )
            context_ids = _collect_episode_events(
                events=episode.context_events,
                events_by_id=events_by_id,
                roles_by_event_id=roles_by_event_id,
                sources_by_id=sources_by_id,
                role=f"{side}_context",
            )
            _collect_episode_events(
                events=episode.omitted_point_events,
                events_by_id=events_by_id,
                roles_by_event_id=roles_by_event_id,
                sources_by_id=sources_by_id,
                role=f"{side}_omitted_point",
            )
            episodes.append(
                _episode_fact(
                    side=side,
                    episode=episode,
                    matched_ids=matched_ids,
                    context_ids=context_ids,
                    episode_index=episode_index,
                )
            )

    for event_id in seed.source_event_ids:
        if event_id in roles_by_event_id:
            roles_by_event_id[event_id].add("seed_source")

    events = tuple(
        _event_fact(event=event, roles=tuple(sorted(roles_by_event_id[event_id])))
        for event_id, event in sorted(events_by_id.items())
    )
    allowed_event_ids = tuple(event.event_id for event in events)
    allowed_source_ids = tuple(sorted(sources_by_id))
    warnings = tuple(
        dict.fromkeys(
            (
                *seed.warnings,
                *compare.warnings,
                *_fact_pack_warnings(events=events, episodes=episodes),
            )
        )
    )
    return ArticleDraftFactPack(
        seed_id=seed.seed_id,
        title=seed.title,
        summary=seed.summary,
        compare_preset_id=seed.compare_preset_id,
        source_event_ids=seed.source_event_ids,
        source_event_titles=seed.source_event_titles,
        compare_summary=compare.deterministic_summary,
        query_vector_similarity=compare.query_vector_similarity,
        shared_primary_cycles=compare.shared_primary_cycles,
        shared_matched_event_ids=compare.shared_matched_event_ids,
        shared_context_event_ids=compare.shared_context_event_ids,
        allowed_event_ids=allowed_event_ids,
        allowed_source_ids=allowed_source_ids,
        events=events,
        sources=tuple(sources_by_id[source_id] for source_id in allowed_source_ids),
        episodes=tuple(episodes),
        warnings=warnings,
        writing_constraints=(
            "Use only event_ids and source_ids present in this fact pack.",
            "Separate matched_events from context_events in the prose.",
            "Do not present symbolic-historical similarity as prediction.",
            "Mention date precision caveats when seed dates use year_start_anchor.",
            "Mark generated text as a draft that requires human editorial review.",
        ),
    )


def build_mock_article_draft(fact_pack: ArticleDraftFactPack) -> ArticleDraftOutput:
    matched_events = [
        event
        for event in fact_pack.events
        if any(role.endswith("_matched") or role == "seed_source" for role in event.roles)
    ][:4]
    context_events = [
        event
        for event in fact_pack.events
        if any(role.endswith("_context") for role in event.roles)
    ][:3]
    used_event_ids = tuple(
        dict.fromkeys(event.event_id for event in matched_events + context_events)
    )
    used_source_ids = tuple(
        dict.fromkeys(
            source_id
            for event in matched_events + context_events
            for source_id in event.source_ids[:1]
        )
    )
    first_source_ids = tuple(
        source_id
        for source_id in (
            matched_events[0].source_ids[:1] if matched_events else used_source_ids[:1]
        )
    )
    evidence_title = ", ".join(event.title for event in matched_events[:3]) or "backend events"
    context_title = (
        ", ".join(event.title for event in context_events)
        or "no separated context events"
    )
    sections = (
        ArticleDraftSection(
            section_id="opening",
            heading="Teza robocza",
            paragraphs=(
                (
                    f"Ten szkic porownuje temat '{fact_pack.title}' przez deterministyczny "
                    "backend Astro Global. To opis podobienstwa symboliczno-historycznego, "
                    "nie prognoza."
                ),
            ),
            claims=(
                ArticleDraftClaim(
                    claim_id="claim_opening_policy",
                    text="Draft uses backend facts only and keeps the non-prediction caveat.",
                    event_ids=matched_events[:1] and (matched_events[0].event_id,) or (),
                    source_ids=first_source_ids,
                ),
            ),
        ),
        ArticleDraftSection(
            section_id="evidence",
            heading="Dowody z backendu",
            paragraphs=(
                (
                    f"Najwazniejsze przywolane wydarzenia to: {evidence_title}. "
                    f"Podobienstwo wektorow zapytania wynosi "
                    f"{fact_pack.query_vector_similarity:.3f}."
                ),
            ),
            claims=(
                ArticleDraftClaim(
                    claim_id="claim_matched_events",
                    text="Matched events are taken from the compare response.",
                    event_ids=tuple(event.event_id for event in matched_events),
                    source_ids=used_source_ids,
                    cycle_labels=fact_pack.shared_primary_cycles,
                ),
            ),
        ),
        ArticleDraftSection(
            section_id="caveats",
            heading="Ograniczenia",
            paragraphs=(
                (
                    f"Kontekst oddzielony od dowodu: {context_title}. Tekst wymaga review "
                    "czlowieka przed publikacja."
                ),
            ),
            claims=(
                ArticleDraftClaim(
                    claim_id="claim_context_separation",
                    text="Context events are not treated as direct matched evidence.",
                    event_ids=(
                        tuple(event.event_id for event in context_events)
                        or tuple(event.event_id for event in matched_events[:1])
                    ),
                    source_ids=tuple(
                        dict.fromkeys(
                            source_id
                            for event in (context_events or matched_events[:1])
                            for source_id in event.source_ids[:1]
                        )
                    ),
                ),
            ),
        ),
    )
    return ArticleDraftOutput(
        seed_id=fact_pack.seed_id,
        title=f"{fact_pack.title} - mock draft",
        sections=sections,
        used_event_ids=used_event_ids,
        used_source_ids=used_source_ids,
        warnings=(
            "Mock draft only; not AI output.",
            "Human editorial review is required before publication.",
        ),
    )


def validate_article_draft(
    *,
    fact_pack: ArticleDraftFactPack,
    draft: ArticleDraftOutput,
) -> ArticleDraftValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    allowed_event_ids = set(fact_pack.allowed_event_ids)
    allowed_source_ids = set(fact_pack.allowed_source_ids)
    allowed_cycle_labels = set(fact_pack.shared_primary_cycles)

    if draft.seed_id != fact_pack.seed_id:
        errors.append("Draft seed_id does not match fact pack seed_id.")
    if draft.content_policy != ARTICLE_DRAFT_CONTENT_POLICY:
        errors.append("Draft content_policy is not the required backend-facts-only policy.")
    if draft.editorial_status != ARTICLE_DRAFT_EDITORIAL_STATUS:
        errors.append("Draft editorial_status must require human review.")
    if set(draft.used_event_ids) - allowed_event_ids:
        errors.append(
            "Draft used_event_ids include values outside fact pack: "
            f"{', '.join(sorted(set(draft.used_event_ids) - allowed_event_ids))}."
        )
    if set(draft.used_source_ids) - allowed_source_ids:
        errors.append(
            "Draft used_source_ids include values outside fact pack: "
            f"{', '.join(sorted(set(draft.used_source_ids) - allowed_source_ids))}."
        )

    for section in draft.sections:
        _validate_text_ids(
            text=" ".join((section.heading, *section.paragraphs)),
            allowed_event_ids=allowed_event_ids,
            allowed_source_ids=allowed_source_ids,
            errors=errors,
        )
        _validate_forbidden_phrases(
            text=" ".join((section.heading, *section.paragraphs)),
            errors=errors,
        )
        for claim in section.claims:
            _validate_claim(
                claim=claim,
                allowed_event_ids=allowed_event_ids,
                allowed_source_ids=allowed_source_ids,
                allowed_cycle_labels=allowed_cycle_labels,
                errors=errors,
                warnings=warnings,
            )

    if not draft.sections:
        errors.append("Draft must contain at least one section.")
    if not draft.used_event_ids:
        errors.append("Draft must declare at least one used_event_id.")
    if not draft.used_source_ids:
        errors.append("Draft must declare at least one used_source_id.")

    return ArticleDraftValidationResult(
        ok=not errors,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _collect_episode_events(
    *,
    events: list[HistoricalEventResponse],
    events_by_id: dict[str, HistoricalEventResponse],
    roles_by_event_id: dict[str, set[str]],
    sources_by_id: dict[str, ArticleSourceFact],
    role: str,
) -> tuple[str, ...]:
    event_ids: list[str] = []
    for event in events:
        event_ids.append(event.event_id)
        events_by_id[event.event_id] = event
        roles_by_event_id[event.event_id].add(role)
        for source in event.sources:
            sources_by_id[source.source_id] = _source_fact(
                event_id=event.event_id,
                source=source,
            )
    return tuple(event_ids)


def _episode_fact(
    *,
    side: Literal["left", "right"],
    episode: ResonanceEpisodeResponse,
    matched_ids: tuple[str, ...],
    context_ids: tuple[str, ...],
    episode_index: int,
) -> ArticleEpisodeFact:
    warnings = []
    if episode.event_coverage.warning:
        warnings.append(episode.event_coverage.warning)
    if episode.narrative_confidence.narrative_confidence < 0.55:
        warnings.append("low_narrative_confidence")
    if episode.event_coverage.events_found == 0:
        warnings.append("thin_history")
    if episode_index > 1:
        warnings.append("secondary_episode")
    return ArticleEpisodeFact(
        side=side,
        period_start=episode.period_start,
        period_end=episode.period_end,
        best_date=episode.best_date,
        score_label=episode.score_breakdown.label,
        narrative_confidence=episode.narrative_confidence.narrative_confidence,
        matched_event_ids=matched_ids,
        context_event_ids=context_ids,
        warnings=tuple(warnings),
    )


def _event_fact(
    *,
    event: HistoricalEventResponse,
    roles: tuple[str, ...],
) -> ArticleEventFact:
    return ArticleEventFact(
        event_id=event.event_id,
        title=event.title,
        display_date=event.display_date,
        start_astro_year=event.start_astro_year,
        end_astro_year=event.end_astro_year,
        category=event.category,
        event_kind=event.event_kind,
        is_ongoing=event.is_ongoing,
        end_year_policy=event.end_year_policy,
        region=event.region,
        geo_scope=event.geo_scope,
        confidence_score=event.confidence_score,
        roles=roles,
        source_ids=tuple(source.source_id for source in event.sources),
    )


def _source_fact(
    *,
    event_id: str,
    source: EventSourceResponse,
) -> ArticleSourceFact:
    return ArticleSourceFact(
        source_id=source.source_id,
        event_id=event_id,
        source_type=source.source_type,
        source_name=source.source_name,
        source_url=source.source_url,
        source_quality=source.source_quality,
        source_precision=source.source_precision,
    )


def _fact_pack_warnings(
    *,
    events: tuple[ArticleEventFact, ...],
    episodes: tuple[ArticleEpisodeFact, ...],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if any(event.event_kind == "long_process" for event in events):
        warnings.append("long_process_events_present")
    if any(
        event.roles and any(role.endswith("_context") for role in event.roles)
        for event in events
    ):
        warnings.append("context_events_must_remain_separate")
    if any(episode.warnings for episode in episodes):
        warnings.append("episode_quality_warnings_present")
    if not any(source_id for event in events for source_id in event.source_ids):
        warnings.append("no_sources_available")
    return tuple(warnings)


def _validate_claim(
    *,
    claim: ArticleDraftClaim,
    allowed_event_ids: set[str],
    allowed_source_ids: set[str],
    allowed_cycle_labels: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    unknown_event_ids = set(claim.event_ids) - allowed_event_ids
    unknown_source_ids = set(claim.source_ids) - allowed_source_ids
    unknown_cycle_labels = set(claim.cycle_labels) - allowed_cycle_labels
    if unknown_event_ids:
        errors.append(
            f"Claim {claim.claim_id} references unknown event_ids: "
            f"{', '.join(sorted(unknown_event_ids))}."
        )
    if unknown_source_ids:
        errors.append(
            f"Claim {claim.claim_id} references unknown source_ids: "
            f"{', '.join(sorted(unknown_source_ids))}."
        )
    if unknown_cycle_labels:
        errors.append(
            f"Claim {claim.claim_id} references unknown cycle labels: "
            f"{', '.join(sorted(unknown_cycle_labels))}."
        )
    if not claim.event_ids and not claim.cycle_labels:
        errors.append(f"Claim {claim.claim_id} has no event or cycle evidence.")
    if claim.event_ids and not claim.source_ids:
        errors.append(f"Claim {claim.claim_id} cites events without source_ids.")
    _validate_text_ids(
        text=claim.text,
        allowed_event_ids=allowed_event_ids,
        allowed_source_ids=allowed_source_ids,
        errors=errors,
    )
    _validate_forbidden_phrases(text=claim.text, errors=errors)
    if claim.cycle_labels and not allowed_cycle_labels:
        warnings.append(f"Claim {claim.claim_id} cites cycles but no shared cycles exist.")


def _validate_text_ids(
    *,
    text: str,
    allowed_event_ids: set[str],
    allowed_source_ids: set[str],
    errors: list[str],
) -> None:
    event_ids_in_text = set(EVENT_ID_PATTERN.findall(text))
    source_ids_in_text = set(SOURCE_ID_PATTERN.findall(text))
    unknown_event_ids = event_ids_in_text - allowed_event_ids
    unknown_source_ids = source_ids_in_text - allowed_source_ids
    if unknown_event_ids:
        errors.append(
            f"Draft text mentions event_ids outside fact pack: "
            f"{', '.join(sorted(unknown_event_ids))}."
        )
    if unknown_source_ids:
        errors.append(
            f"Draft text mentions source_ids outside fact pack: "
            f"{', '.join(sorted(unknown_source_ids))}."
        )


def _validate_forbidden_phrases(*, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for phrase in FORBIDDEN_DRAFT_PHRASES:
        if phrase in lowered:
            errors.append(f"Draft contains forbidden predictive phrase: {phrase!r}.")
