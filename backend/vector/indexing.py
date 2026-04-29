"""backend.vector.indexing — deterministic upsert helpers.

All public functions derive a UUID5 record_id from the content key so
repeated indexing of the same item is idempotent (safe to call multiple
times with the same data).
"""
from __future__ import annotations

import time
from typing import Any

from .collections  import HOOKS, PRODUCTS, CAMPAIGNS, SIGNALS, PATTERNS, ANGLES, CREATIVES
from .normalization import deterministic_id, stamp_lineage, normalize
from .schemas       import VectorRecord


# ── low-level record builders ─────────────────────────────────────────────────


def make_record(
    *,
    source: str,
    key: str,
    collection: str,
    vector: list[float],
    payload: dict[str, Any],
    sequence_id: str = "",
    normalize_vec: bool = True,
) -> VectorRecord:
    """Build a ``VectorRecord`` with deterministic ID and lineage stamp."""
    vec = normalize(vector) if normalize_vec else vector
    pid = deterministic_id(source, key)
    return VectorRecord(
        record_id=pid,
        vector=vec,
        payload=stamp_lineage(payload, source=source, sequence_id=sequence_id),
        collection=collection,
        source=source,
        sequence_id=sequence_id,
    )


# ── domain-specific builders ──────────────────────────────────────────────────


def hook_record(hook: str, vector: list[float], **meta: Any) -> VectorRecord:
    return make_record(
        source="hook", key=hook, collection=HOOKS,
        vector=vector, payload={"text": hook, **meta},
    )


def product_record(product: str, vector: list[float], **meta: Any) -> VectorRecord:
    return make_record(
        source="product", key=product, collection=PRODUCTS,
        vector=vector, payload={"name": product, **meta},
    )


def angle_record(angle: str, vector: list[float], **meta: Any) -> VectorRecord:
    return make_record(
        source="angle", key=angle, collection=ANGLES,
        vector=vector, payload={"text": angle, **meta},
    )


def campaign_record(
    campaign_id: str,
    vector: list[float],
    product: str = "",
    hook: str = "",
    angle: str = "",
    **meta: Any,
) -> VectorRecord:
    return make_record(
        source="campaign", key=campaign_id, collection=CAMPAIGNS,
        vector=vector,
        payload={"campaign_id": campaign_id, "product": product,
                 "hook": hook, "angle": angle, **meta},
    )


def signal_record(
    signal_key: str,
    vector: list[float],
    signal_type: str = "",
    **meta: Any,
) -> VectorRecord:
    return make_record(
        source="signal", key=signal_key, collection=SIGNALS,
        vector=vector,
        payload={"key": signal_key, "signal_type": signal_type, **meta},
    )


def pattern_record(
    pattern_key: str,
    vector: list[float],
    hook: str = "",
    angle: str = "",
    score: float = 0.0,
    **meta: Any,
) -> VectorRecord:
    return make_record(
        source="pattern", key=pattern_key, collection=PATTERNS,
        vector=vector,
        payload={"key": pattern_key, "hook": hook, "angle": angle,
                 "score": score, **meta},
    )


def creative_record(
    creative_id: str,
    vector: list[float],
    hook: str = "",
    product: str = "",
    roas: float = 0.0,
    **meta: Any,
) -> VectorRecord:
    return make_record(
        source="creative", key=creative_id, collection=CREATIVES,
        vector=vector,
        payload={"creative_id": creative_id, "hook": hook,
                 "product": product, "roas": roas, **meta},
    )


# ── batch indexing ────────────────────────────────────────────────────────────


def index_batch(records: list[VectorRecord], store=None) -> int:
    """Upsert *records* into *store* (defaults to module singleton).

    Returns the count of records written.
    """
    if not records:
        return 0
    if store is None:
        from .qdrant_client import get_store
        store = get_store()
    return store.upsert(records)


def index_hooks(
    hook_vectors: dict[str, list[float]],
    store=None,
    **meta: Any,
) -> int:
    """Upsert a ``{hook_text: vector}`` mapping into the hooks collection."""
    records = [hook_record(h, v, **meta) for h, v in hook_vectors.items()]
    return index_batch(records, store=store)


def index_products(
    product_vectors: dict[str, list[float]],
    store=None,
    **meta: Any,
) -> int:
    records = [product_record(p, v, **meta) for p, v in product_vectors.items()]
    return index_batch(records, store=store)


def index_angles(
    angle_vectors: dict[str, list[float]],
    store=None,
    **meta: Any,
) -> int:
    records = [angle_record(a, v, **meta) for a, v in angle_vectors.items()]
    return index_batch(records, store=store)
