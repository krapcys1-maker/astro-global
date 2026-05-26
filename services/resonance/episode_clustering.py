from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class CandidatePoint:
    date: date
    score: float
    row_index: int
    percentile: float = 0.0


@dataclass(frozen=True)
class ResonanceEpisode:
    period_start: date
    period_end: date
    best_date: date
    best_score: float
    best_percentile: float
    row_indices: tuple[int, ...]


@dataclass(frozen=True)
class EpisodeEventProfile:
    event_ids: frozenset[str] = frozenset()
    long_process_event_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SuppressedNearbyMatch:
    episode: ResonanceEpisode
    reason: str
    event_overlap: float


@dataclass(frozen=True)
class DiverseResonanceEpisode:
    episode: ResonanceEpisode
    related_windows: tuple[SuppressedNearbyMatch, ...] = ()


def _episode_from_points(points: list[CandidatePoint], padding_days: int) -> ResonanceEpisode:
    best = max(points, key=lambda item: item.score)
    return ResonanceEpisode(
        period_start=points[0].date - timedelta(days=padding_days),
        period_end=points[-1].date + timedelta(days=padding_days),
        best_date=best.date,
        best_score=best.score,
        best_percentile=best.percentile,
        row_indices=tuple(point.row_index for point in points),
    )


def cluster_candidate_points(
    points: list[CandidatePoint],
    max_episode_gap_days: int = 45,
    min_independent_episode_separation_days: int = 365,
    padding_days: int = 0,
) -> list[ResonanceEpisode]:
    if not points:
        return []
    ordered = sorted(points, key=lambda item: item.date)
    clusters: list[list[CandidatePoint]] = [[ordered[0]]]
    for point in ordered[1:]:
        if (point.date - clusters[-1][-1].date).days <= max_episode_gap_days:
            clusters[-1].append(point)
        else:
            clusters.append([point])

    episodes = [_episode_from_points(cluster, padding_days=padding_days) for cluster in clusters]
    by_score = sorted(episodes, key=lambda item: item.best_score, reverse=True)
    independent: list[ResonanceEpisode] = []
    for episode in by_score:
        if all(
            abs((episode.best_date - existing.best_date).days)
            >= min_independent_episode_separation_days
            for existing in independent
        ):
            independent.append(episode)
    return sorted(independent, key=lambda item: item.best_score, reverse=True)


def select_diverse_episodes(
    episodes: Sequence[ResonanceEpisode],
    *,
    max_episodes: int,
    event_profiles: Mapping[ResonanceEpisode, EpisodeEventProfile] | None = None,
    default_min_year_gap: int = 5,
    pre_1900_event_min_year_gap: int = 10,
    event_overlap_threshold: float = 0.60,
) -> list[DiverseResonanceEpisode]:
    """Choose UI-facing historical analogues without repeating the same peak."""
    if max_episodes <= 0:
        return []

    profiles = event_profiles or {}
    selected: list[ResonanceEpisode] = []
    related: dict[ResonanceEpisode, list[SuppressedNearbyMatch]] = {}

    for episode in sorted(episodes, key=lambda item: item.best_score, reverse=True):
        suppress_to: ResonanceEpisode | None = None
        suppress_reason = ""
        suppress_overlap = 0.0
        for existing in selected:
            reason, overlap = _suppression_reason(
                candidate=episode,
                selected=existing,
                candidate_profile=profiles.get(episode, EpisodeEventProfile()),
                selected_profile=profiles.get(existing, EpisodeEventProfile()),
                default_min_year_gap=default_min_year_gap,
                pre_1900_event_min_year_gap=pre_1900_event_min_year_gap,
                event_overlap_threshold=event_overlap_threshold,
            )
            if reason:
                suppress_to = existing
                suppress_reason = reason
                suppress_overlap = overlap
                break

        if suppress_to is not None:
            related.setdefault(suppress_to, []).append(
                SuppressedNearbyMatch(
                    episode=episode,
                    reason=suppress_reason,
                    event_overlap=suppress_overlap,
                )
            )
            continue

        if len(selected) < max_episodes:
            selected.append(episode)

    return [
        DiverseResonanceEpisode(
            episode=episode,
            related_windows=tuple(
                sorted(
                    related.get(episode, []),
                    key=lambda item: item.episode.best_score,
                    reverse=True,
                )
            ),
        )
        for episode in selected
    ]


def _suppression_reason(
    *,
    candidate: ResonanceEpisode,
    selected: ResonanceEpisode,
    candidate_profile: EpisodeEventProfile,
    selected_profile: EpisodeEventProfile,
    default_min_year_gap: int,
    pre_1900_event_min_year_gap: int,
    event_overlap_threshold: float,
) -> tuple[str, float]:
    year_gap = abs((candidate.best_date - selected.best_date).days) / 365.25
    event_overlap = _event_overlap_ratio(
        candidate_profile.event_ids,
        selected_profile.event_ids,
    )

    if event_overlap > event_overlap_threshold:
        return "event_overlap_gt_60_percent", event_overlap
    if year_gap < default_min_year_gap:
        return f"within_{default_min_year_gap}_year_cooldown", event_overlap
    if (
        candidate.best_date.year < 1900
        and selected.best_date.year < 1900
        and year_gap < pre_1900_event_min_year_gap
        and event_overlap > event_overlap_threshold
    ):
        return f"pre_1900_{pre_1900_event_min_year_gap}_year_event_cooldown", event_overlap
    if (
        candidate_profile.long_process_event_ids & selected_profile.long_process_event_ids
        and year_gap < pre_1900_event_min_year_gap
    ):
        return "same_long_historical_process", event_overlap
    return "", event_overlap


def _event_overlap_ratio(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))
