"""backend.vector.similarity — cosine similarity utilities."""
from __future__ import annotations
import math


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 on dimension mismatch."""
    if len(a) != len(b) or not a:
        return 0.0
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(x * x for x in b))
    denom = na * nb
    return dot / denom if denom > 1e-12 else 0.0


def dot_product(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def batch_cosine(query: list[float], candidates: list[list[float]]) -> list[float]:
    """Return cosine score of *query* against each candidate."""
    return [cosine(query, c) for c in candidates]


def affinity_matrix(vectors: list[list[float]]) -> list[list[float]]:
    """NxN cosine similarity matrix for *vectors*."""
    n = len(vectors)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s = cosine(vectors[i], vectors[j])
            matrix[i][j] = s
            matrix[j][i] = s
    return matrix


def top_k(
    query: list[float],
    candidates: dict[str, list[float]],
    k: int = 10,
    threshold: float = 0.0,
) -> list[tuple[str, float]]:
    """Return top-k (key, score) pairs sorted descending by cosine similarity."""
    scored = [
        (key, cosine(query, vec))
        for key, vec in candidates.items()
    ]
    scored = [(k_, s) for k_, s in scored if s >= threshold]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
