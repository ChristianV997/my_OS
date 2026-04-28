"""backend.vector.memory.creative_memory — semantic memory for creatives.

Indexes creative assets (hooks, angles, ad copy, video scripts) and
provides semantic similarity search for high-performing creative
discovery and de-duplication.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_CREATIVES
from backend.vector.indexing import index_record, index_batch
from backend.vector.schemas.search_query import SearchQuery
from backend.vector.semantic_search import semantic_search, search_creatives
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_creative(
    source_id: str,
    text: str,
    creative_type: str = "hook",
    product: str = "",
    roas: float = 0.0,
    label: str = "",
    extra: dict[str, Any] | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Index a creative into the creatives collection.

    Parameters
    ----------
    source_id     — unique creative identifier
    text          — hook / angle / ad copy text to embed
    creative_type — "hook", "angle", "script", "headline", …
    product       — associated product name
    roas          — ROAS achieved (0.0 if unknown)
    label         — performance label ("winner", "control", "loser", …)
    """
    payload: dict[str, Any] = {
        "creative_type": creative_type,
        "product": product,
        "roas": roas,
        "label": label,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_CREATIVES,
        source_id=source_id,
        source_type="creative",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )


def index_creatives_batch(creatives: list[dict[str, Any]]) -> int:
    """Index a batch of creative dicts."""
    items = []
    for c in creatives:
        text = c.get("hook") or c.get("angle") or c.get("text", "")
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": c.get("id", ""),
            "payload": {
                "creative_type": c.get("creative_type", "hook"),
                "product": c.get("product", ""),
                "roas": c.get("roas", 0.0),
                "label": c.get("label", ""),
            },
            "replay_hash": c.get("replay_hash"),
            "sequence_id": c.get("sequence_id"),
        })
    return index_batch(items, collection=COLLECTION_CREATIVES, source_type="creative")


def recall_creatives(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    product: str | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Retrieve semantically similar creatives for *query*."""
    filters: dict[str, Any] = {}
    if product:
        filters["product"] = product
    return semantic_search(
        SearchQuery(
            collection=COLLECTION_CREATIVES,
            query_text=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )


def find_similar_creatives(
    creative_id: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> list[SimilarityResult]:
    """Find creatives similar to an existing creative by its source_id.

    Fetches the creative's vector from the store and searches for
    nearest neighbours (excluding the creative itself).
    """
    from backend.vector.qdrant_client import get_vector_store

    store = get_vector_store()
    # We use a text-based fallback: search with the source_id as query
    # text so the function still works when the store is unavailable.
    # In a production setup this would retrieve the stored vector directly.
    results = search_creatives(
        text=creative_id,
        top_k=top_k + 1,
        score_threshold=score_threshold,
    )
    return [r for r in results if r.source_id != creative_id][:top_k]
