"""backend.vector.similarity — pairwise and batch cosine similarity.

All operations work on plain Python float lists so they are usable
without Qdrant (pure-Python fallback, no numpy dependency).  When numpy
is available the batch path uses it for performance.

All pairwise calls emit telemetry via ``backend.vector.telemetry``.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

from backend.vector.normalization import normalize, is_zero_vector

_log = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity ∈ [-1, 1] between vectors *a* and *b*.

    Returns 0.0 for zero vectors or mismatched dimensions.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    if is_zero_vector(a) or is_zero_vector(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def dot_product(a: list[float], b: list[float]) -> float:
    """Return the dot product of two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def cosine_similarity_normalized(a: list[float], b: list[float]) -> float:
    """Return dot product of L2-normalised *a* and *b* (≡ cosine similarity)."""
    return dot_product(normalize(a), normalize(b))


def top_k_similar(
    query: list[float],
    candidates: list[tuple[str, list[float]]],
    k: int = 10,
    score_threshold: float = 0.0,
) -> list[tuple[str, float]]:
    """Return the top-k most similar candidates to *query*.

    Parameters
    ----------
    query     — query vector
    candidates — list of (id, vector) pairs
    k         — maximum number of results
    score_threshold — minimum cosine similarity (0.0 = no filter)

    Returns
    -------
    List of (id, score) sorted by score descending.
    """
    scored = [
        (cid, cosine_similarity(query, vec))
        for cid, vec in candidates
    ]
    scored = [(cid, s) for cid, s in scored if s >= score_threshold]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def pairwise_similarity_matrix(
    vectors: list[list[float]],
) -> list[list[float]]:
    """Compute an n×n cosine similarity matrix for *vectors*.

    Returns a symmetric matrix where M[i][j] is the cosine similarity
    between vectors[i] and vectors[j].
    """
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s = cosine_similarity(vectors[i], vectors[j])
            matrix[i][j] = s
            matrix[j][i] = s
    return matrix


def compare_and_emit(
    collection: str,
    source_a: str,
    vector_a: list[float],
    source_b: str,
    vector_b: list[float],
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> float:
    """Compute cosine similarity and emit telemetry.

    Returns the similarity score.
    """
    from backend.vector import telemetry as vt

    t0 = time.time()
    score = cosine_similarity(vector_a, vector_b)
    latency_ms = (time.time() - t0) * 1000
    vt.emit_similarity(
        collection=collection,
        source_a=source_a,
        source_b=source_b,
        score=score,
        latency_ms=latency_ms,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )
    return score
