"""semantic_compression — merge and deduplicate SemanticStore units.

Reads all existing semantic units, identifies near-duplicate clusters
(cosine similarity above threshold), merges them into a single unit
carrying the union of cluster members and the average embedding, and
removes the originals.  Bumps the SemanticStore generation counter.
"""
from __future__ import annotations

import logging
import uuid
import time
from typing import Any

from .policies.compression_policy import CompressionPolicy

log = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na  = sum(x * x for x in a) ** 0.5
    nb  = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if (na * nb) > 1e-12 else 0.0


def _merge_units(units: list[Any], generation: int) -> Any:
    """Merge a list of SemanticUnit objects into a single representative unit."""
    from backend.memory.semantic.store import SemanticUnit
    from backend.vector.normalization  import normalize

    all_members: list[str]       = []
    all_vecs:    list[list[float]] = []
    best_score = 0.0

    for u in units:
        all_members.extend(u.cluster_members)
        if u.embedding:
            all_vecs.append(u.embedding)
        best_score = max(best_score, u.score)

    merged_embedding: list[float] = []
    if all_vecs:
        dim = len(all_vecs[0])
        avg = [sum(v[i] for v in all_vecs) / len(all_vecs) for i in range(dim)]
        merged_embedding = normalize(avg)

    merged_members = list(dict.fromkeys(all_members))  # dedup, preserve order
    label          = min(merged_members, key=len) if merged_members else "merged"

    return SemanticUnit(
        unit_id=uuid.uuid4().hex[:12],
        label=label,
        domain=units[0].domain,
        embedding=merged_embedding,
        cluster_members=merged_members,
        score=best_score,
        generation=generation,
        metadata={"merged_from": [u.unit_id for u in units]},
    )


def compress_domain(
    domain: str,
    policy: CompressionPolicy | None = None,
) -> tuple[int, int]:
    """Merge near-duplicate units in *domain*. Returns (merged_count, pruned_count)."""
    policy = policy or CompressionPolicy()
    try:
        from backend.memory.semantic import get_semantic_store
    except Exception:
        return 0, 0

    store   = get_semantic_store()
    units   = store.domain_units(domain)
    if len(units) < 2:
        return 0, 0

    # Greedy similarity clustering: group units with sim > threshold
    merged_out = 0
    pruned_out = 0
    used: set[str] = set()
    generation = store.generation()

    for i, u in enumerate(units):
        if u.unit_id in used:
            continue
        similar = [u]
        for j in range(i + 1, len(units)):
            v = units[j]
            if v.unit_id in used:
                continue
            if (u.embedding and v.embedding and
                    _cosine(u.embedding, v.embedding) >= policy.similarity_threshold):
                similar.append(v)
                used.add(v.unit_id)

        if len(similar) > 1:
            merged = _merge_units(similar, generation)
            store.upsert(merged)
            merged_out += 1
            pruned_out += len(similar)
        used.add(u.unit_id)

    store.bump_generation()
    return merged_out, pruned_out


def compress_all(policy: CompressionPolicy | None = None) -> dict[str, tuple[int, int]]:
    """Compress all domains. Returns {domain: (merged, pruned)}."""
    policy  = policy or CompressionPolicy()
    results = {}
    domains = ["hook", "angle", "signal", "product", "campaign"]
    for domain in domains:
        m, p = compress_domain(domain, policy)
        if m or p:
            results[domain] = (m, p)
    return results
