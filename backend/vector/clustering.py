"""backend.vector.clustering — lightweight vector clustering utilities.

Provides k-means clustering over in-memory float vectors without
requiring heavy ML dependencies.  When scikit-learn is available, the
standard KMeans implementation is used.  Otherwise a pure-Python
mini-batch k-means fallback is used (slower but dependency-free).

All clustering operations emit telemetry via ``backend.vector.telemetry``.
"""
from __future__ import annotations

import logging
import math
import random
import time
from typing import Any

_log = logging.getLogger(__name__)


# ── pure-Python k-means fallback ──────────────────────────────────────────────

def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    return [sum(v[d] for v in vectors) / len(vectors) for d in range(dim)]


def _kmeans_pure(
    vectors: list[list[float]],
    k: int,
    max_iter: int = 100,
    seed: int = 42,
) -> list[int]:
    """Pure-Python k-means returning a cluster label per vector."""
    rng = random.Random(seed)
    indices = rng.sample(range(len(vectors)), min(k, len(vectors)))
    centroids = [list(vectors[i]) for i in indices]

    labels = [0] * len(vectors)
    for _ in range(max_iter):
        new_labels = []
        for vec in vectors:
            dists = [_euclidean(vec, c) for c in centroids]
            new_labels.append(dists.index(min(dists)))
        if new_labels == labels:
            break
        labels = new_labels
        for ci in range(len(centroids)):
            cluster_vecs = [vectors[j] for j, lbl in enumerate(labels) if lbl == ci]
            if cluster_vecs:
                centroids[ci] = _centroid(cluster_vecs)
    return labels


def _kmeans_sklearn(
    vectors: list[list[float]],
    k: int,
    max_iter: int = 100,
    seed: int = 42,
) -> list[int]:
    """scikit-learn k-means returning a cluster label per vector."""
    from sklearn.cluster import KMeans
    import numpy as np

    arr = np.array(vectors, dtype=float)
    km = KMeans(n_clusters=k, max_iter=max_iter, random_state=seed, n_init=5)
    return km.fit_predict(arr).tolist()


# ── public API ────────────────────────────────────────────────────────────────

def cluster_vectors(
    vectors: list[list[float]],
    k: int,
    ids: list[str] | None = None,
    collection: str = "",
    max_iter: int = 100,
    seed: int = 42,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> dict[str, Any]:
    """Cluster *vectors* into *k* groups.

    Parameters
    ----------
    vectors    — list of float vectors (must all share same dimension)
    k          — number of clusters
    ids        — optional parallel list of record IDs for labelling
    collection — source collection name (for telemetry)
    max_iter   — maximum k-means iterations
    seed       — random seed for reproducibility
    replay_hash / sequence_id — lineage fields passed to telemetry

    Returns
    -------
    dict with keys:
      "labels"   — list[int] cluster assignments per vector
      "k"        — actual k used
      "n_vectors" — number of vectors clustered
      "clusters"  — dict[int, list[str]] mapping cluster_id → record IDs
    """
    from backend.vector import telemetry as vt

    if not vectors:
        return {"labels": [], "k": k, "n_vectors": 0, "clusters": {}}

    actual_k = min(k, len(vectors))
    t0 = time.time()
    try:
        labels = _kmeans_sklearn(vectors, actual_k, max_iter=max_iter, seed=seed)
    except Exception:
        labels = _kmeans_pure(vectors, actual_k, max_iter=max_iter, seed=seed)

    latency_ms = (time.time() - t0) * 1000

    clusters: dict[int, list[str]] = {ci: [] for ci in range(actual_k)}
    for idx, label in enumerate(labels):
        rid = ids[idx] if ids and idx < len(ids) else str(idx)
        clusters[label].append(rid)

    vt.emit_cluster(
        collection=collection,
        n_vectors=len(vectors),
        n_clusters=actual_k,
        latency_ms=latency_ms,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )

    return {
        "labels": labels,
        "k": actual_k,
        "n_vectors": len(vectors),
        "clusters": clusters,
    }


def find_cluster_representatives(
    vectors: list[list[float]],
    labels: list[int],
    ids: list[str] | None = None,
) -> dict[int, str]:
    """Return the record ID closest to each cluster centroid.

    Returns dict mapping cluster_id → representative record ID.
    """
    if not vectors or not labels:
        return {}
    k = max(labels) + 1
    representatives: dict[int, str] = {}
    for ci in range(k):
        cluster_indices = [i for i, lbl in enumerate(labels) if lbl == ci]
        if not cluster_indices:
            continue
        cluster_vecs = [vectors[i] for i in cluster_indices]
        centroid = _centroid(cluster_vecs)
        best_idx = min(
            cluster_indices,
            key=lambda i: _euclidean(vectors[i], centroid),
        )
        rid = ids[best_idx] if ids and best_idx < len(ids) else str(best_idx)
        representatives[ci] = rid
    return representatives
