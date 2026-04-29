"""cluster_abstraction — cluster raw episodes into candidate semantic units.

Takes a ReplayBatch, extracts text-bearing events (decision.logged,
signals.updated, inference.completed), embeds them, clusters them using
spherical k-means, and returns candidate SemanticUnit objects for upsert
into SemanticStore.
"""
from __future__ import annotations

import uuid
import time
import logging
from typing import Any

from .schemas.replay_batch import ReplayBatch
from .policies.compression_policy import CompressionPolicy

log = logging.getLogger(__name__)

# Map event type → the field containing the meaningful text
_TEXT_FIELDS: dict[str, tuple[str, str]] = {
    "decision.logged":       ("hook",    "hook"),
    "signals.updated":       ("signals", "signal"),   # list field
    "inference.completed":   ("content", "hook"),
    "campaign.launched":     ("hook",    "hook"),
    "vector.indexed":        ("source",  "signal"),
}


def extract_text_items(batch: ReplayBatch) -> dict[str, list[str]]:
    """Return {domain: [text, ...]} from events in the batch."""
    result: dict[str, list[str]] = {}
    for ev in batch.events:
        ev_type = ev.get("type", "")
        if ev_type not in _TEXT_FIELDS:
            continue
        field_name, domain = _TEXT_FIELDS[ev_type]
        raw = ev.get(field_name, "")
        if isinstance(raw, list):
            texts = [str(item.get("keyword") or item.get("text") or item)
                     for item in raw if item]
        elif isinstance(raw, str) and raw:
            texts = [raw]
        else:
            continue
        result.setdefault(domain, []).extend(texts)
    return result


def cluster_domain(
    texts: list[str],
    domain: str,
    policy: CompressionPolicy,
) -> list[dict[str, Any]]:
    """Embed texts, cluster them, return candidate semantic unit dicts."""
    if len(texts) < policy.min_cluster_size:
        return []

    try:
        from backend.vector.embeddings import embed_batch
        from backend.vector.clustering import kmeans, _centroid
        from backend.vector.normalization import normalize
    except Exception as exc:
        log.warning("cluster_abstraction: embedding unavailable (%s)", exc)
        return []

    vecs = embed_batch(texts)
    if not vecs:
        return []

    k = policy.cluster_count(len(texts))
    _, labels = kmeans(vecs, k=k, seed=42)

    clusters: dict[int, list[tuple[str, list[float]]]] = {}
    for text, vec, label in zip(texts, vecs, labels):
        clusters.setdefault(label, []).append((text, vec))

    units = []
    for cluster_id, members in clusters.items():
        if not policy.cluster_is_significant(len(members)):
            continue
        member_texts = [m[0] for m in members]
        member_vecs  = [m[1] for m in members]
        centroid     = normalize(_centroid(member_vecs))
        label        = _label_for_cluster(member_texts)
        units.append({
            "unit_id":         uuid.uuid4().hex[:12],
            "label":           label,
            "domain":          domain,
            "embedding":       centroid,
            "cluster_members": member_texts,
            "score":           len(members) / max(len(texts), 1),
            "ts":              time.time(),
        })
    return units


def _label_for_cluster(texts: list[str]) -> str:
    """Heuristic: use the shortest text as the cluster label."""
    return min(texts, key=len) if texts else "cluster"


def abstract_batch(
    batch: ReplayBatch,
    policy: CompressionPolicy | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Full pipeline: extract texts → cluster → return {domain: [unit_dict]}."""
    policy = policy or CompressionPolicy()
    if not policy.should_compress(batch.size):
        return {}

    text_map = extract_text_items(batch)
    result   = {}
    for domain, texts in text_map.items():
        unique = list(dict.fromkeys(texts))  # deduplicate, preserve order
        units  = cluster_domain(unique, domain, policy)
        if units:
            result[domain] = units
    return result
