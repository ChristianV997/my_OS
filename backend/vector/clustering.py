"""backend.vector.clustering — k-means winner clustering over vector collections.

Uses stdlib only (no sklearn dependency) so it is always available.
For large-scale use, swap _kmeans for sklearn.cluster.KMeans.
"""
from __future__ import annotations
import math
import random
from typing import Any

from .similarity import cosine


# ── pure-python k-means ───────────────────────────────────────────────────────

def _norm(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 1e-12 else v


def _centroid(vecs: list[list[float]]) -> list[float]:
    if not vecs:
        return []
    dim = len(vecs[0])
    c = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
    return _norm(c)


def kmeans(
    vectors: list[list[float]],
    k: int,
    max_iter: int = 50,
    seed: int = 42,
) -> tuple[list[list[float]], list[int]]:
    """K-means on unit vectors (spherical k-means via cosine similarity).

    Returns (centroids, labels).
    """
    n = len(vectors)
    if n == 0 or k <= 0:
        return [], []
    k = min(k, n)

    rng = random.Random(seed)
    indices = rng.sample(range(n), k)
    centroids = [list(vectors[i]) for i in indices]

    labels = [0] * n
    for _ in range(max_iter):
        # Assignment
        new_labels = []
        for v in vectors:
            best = max(range(k), key=lambda j: cosine(v, centroids[j]))
            new_labels.append(best)

        if new_labels == labels:
            break
        labels = new_labels

        # Update centroids
        for j in range(k):
            members = [vectors[i] for i, lbl in enumerate(labels) if lbl == j]
            if members:
                centroids[j] = _centroid(members)

    return centroids, labels


# ── high-level clustering helpers ─────────────────────────────────────────────


def cluster_hooks(
    hook_vectors: dict[str, list[float]],
    k: int = 5,
    seed: int = 42,
) -> dict[int, list[str]]:
    """Cluster hooks into k groups. Returns {cluster_id: [hook_text, ...]}."""
    if not hook_vectors:
        return {}
    keys   = list(hook_vectors.keys())
    vecs   = [hook_vectors[h] for h in keys]
    _, labels = kmeans(vecs, k=k, seed=seed)
    groups: dict[int, list[str]] = {}
    for key, lbl in zip(keys, labels):
        groups.setdefault(lbl, []).append(key)
    return groups


def winner_centroid(
    hook_vectors: dict[str, list[float]],
    scores: dict[str, float],
    top_n: int = 10,
) -> list[float]:
    """Compute the centroid of the top-N scoring hooks.

    Useful for finding the embedding 'direction' of winning creatives.
    """
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    winners = [hook for hook, _ in ranked if hook in hook_vectors]
    if not winners:
        return []
    vecs = [hook_vectors[h] for h in winners]
    return _centroid(vecs)


def cluster_records_by_payload(
    records: list[Any],
    key: str,
    k: int = 5,
    seed: int = 42,
) -> dict[int, list[Any]]:
    """Cluster ``SimilarityResult`` records by their vector (uses payload key for label).

    *records* must have ``.vector`` attribute or be dicts with ``"vector"`` key.
    """
    if not records:
        return {}
    def _vec(r: Any) -> list[float]:
        return r.vector if hasattr(r, "vector") else r.get("vector", [])

    vecs = [_vec(r) for r in records]
    _, labels = kmeans(vecs, k=k, seed=seed)
    groups: dict[int, list[Any]] = {}
    for rec, lbl in zip(records, labels):
        groups.setdefault(lbl, []).append(rec)
    return groups
