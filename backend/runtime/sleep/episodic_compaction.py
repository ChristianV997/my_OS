"""episodic_compaction — compress raw episodes into abstraction batches.

Reads a ReplayBatch, calls cluster_abstraction to produce candidate
SemanticUnit dicts, upserts them into SemanticStore, and optionally
indexes their centroids into the vector layer.

This is the primary pathway by which raw episodic events become
long-term semantic memories.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .schemas.replay_batch        import ReplayBatch
from .policies.compression_policy import CompressionPolicy
from .cluster_abstraction         import abstract_batch

log = logging.getLogger(__name__)


def compact(
    batch: ReplayBatch,
    policy: CompressionPolicy | None = None,
    index_vectors: bool = True,
) -> dict[str, int]:
    """Run episodic compaction on *batch*.

    Returns {domain: units_created}.
    """
    policy      = policy or CompressionPolicy()
    domain_units = abstract_batch(batch, policy)

    if not domain_units:
        return {}

    try:
        from backend.memory.semantic.store import SemanticUnit
        from backend.memory.semantic       import get_semantic_store
        store = get_semantic_store()
    except Exception as exc:
        log.warning("episodic_compaction: semantic store unavailable (%s)", exc)
        return {}

    generation = store.generation()
    counts: dict[str, int] = {}

    for domain, unit_dicts in domain_units.items():
        for ud in unit_dicts:
            unit = SemanticUnit(
                unit_id=ud["unit_id"],
                label=ud["label"],
                domain=domain,
                embedding=ud.get("embedding", []),
                cluster_members=ud.get("cluster_members", []),
                score=ud.get("score", 0.5),
                generation=generation + 1,
            )
            store.upsert(unit)
            counts[domain] = counts.get(domain, 0) + 1

    store.bump_generation()

    if index_vectors:
        _index_to_vector_layer(domain_units)

    return counts


def _index_to_vector_layer(domain_units: dict[str, list[dict[str, Any]]]) -> None:
    """Upsert semantic unit centroids into the vector cognition layer."""
    try:
        from backend.vector.indexing    import pattern_record, index_batch
        from backend.vector.qdrant_client import get_store
        store   = get_store()
        records = []
        for domain, units in domain_units.items():
            for ud in units:
                emb = ud.get("embedding", [])
                if not emb:
                    continue
                rec = pattern_record(
                    pattern_key=f"semantic:{domain}:{ud['label']}",
                    vector=emb,
                    hook=ud["label"] if domain == "hook" else "",
                    angle=ud["label"] if domain == "angle" else "",
                    score=ud.get("score", 0.0),
                    domain=domain,
                    source="sleep_compaction",
                )
                records.append(rec)
        if records:
            index_batch(records, store=store)
    except Exception as exc:
        log.debug("_index_to_vector_layer failed: %s", exc)
