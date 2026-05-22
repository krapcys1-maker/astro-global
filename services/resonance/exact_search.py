from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SearchHit:
    row_index: int
    score: float
    percentile: float


def cosine_similarity_matrix(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    if matrix.ndim != 2:
        msg = "matrix must be 2-dimensional"
        raise ValueError(msg)
    if query.ndim != 1:
        msg = "query must be 1-dimensional"
        raise ValueError(msg)
    if matrix.shape[1] != query.shape[0]:
        msg = "matrix and query dimensions do not match"
        raise ValueError(msg)

    matrix_norms = np.linalg.norm(matrix, axis=1)
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        return np.zeros(matrix.shape[0], dtype=np.float64)
    denominator = matrix_norms * query_norm
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.divide(
            matrix @ query, denominator, out=np.zeros(matrix.shape[0]), where=denominator != 0
        )


def exact_search(matrix: np.ndarray, query: np.ndarray, top_k: int = 10) -> list[SearchHit]:
    scores = cosine_similarity_matrix(matrix, query)
    if len(scores) == 0:
        return []
    order = np.argsort(scores)[::-1][:top_k]
    sorted_scores = np.sort(scores)
    hits: list[SearchHit] = []
    for row_index in order:
        percentile = float(
            np.searchsorted(sorted_scores, scores[row_index], side="right") / len(sorted_scores)
        )
        hits.append(
            SearchHit(
                row_index=int(row_index), score=float(scores[row_index]), percentile=percentile
            )
        )
    return hits
