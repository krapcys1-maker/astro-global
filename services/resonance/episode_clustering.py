from __future__ import annotations

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
