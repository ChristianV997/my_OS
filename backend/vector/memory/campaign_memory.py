"""backend.vector.memory.campaign_memory — semantic memory for campaigns.

Indexes campaign execution summaries and provides semantic retrieval
for campaign pattern matching, budget planning, and trend discovery.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_CAMPAIGNS
from backend.vector.indexing import index_record, index_batch
from backend.vector.schemas.search_query import SearchQuery
from backend.vector.semantic_search import semantic_search
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_campaign(
    source_id: str,
    text: str,
    product: str = "",
    phase: str = "",
    roas: float = 0.0,
    spend: float = 0.0,
    status: str = "",
    extra: dict[str, Any] | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Index a campaign summary into the campaigns collection.

    Parameters
    ----------
    source_id — unique campaign identifier
    text      — campaign description / summary to embed
    product   — target product
    phase     — runtime phase ("EXPLORE", "EXPLOIT", …)
    roas      — return on ad spend
    spend     — total spend
    status    — campaign status ("active", "completed", "paused")
    """
    payload: dict[str, Any] = {
        "product": product,
        "phase": phase,
        "roas": roas,
        "spend": spend,
        "status": status,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_CAMPAIGNS,
        source_id=source_id,
        source_type="campaign",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )


def index_campaigns_batch(campaigns: list[dict[str, Any]]) -> int:
    """Index a batch of campaign dicts."""
    items = []
    for c in campaigns:
        text = c.get("description") or c.get("text") or c.get("product", "")
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": c.get("id", c.get("campaign_id", "")),
            "payload": {
                "product": c.get("product", ""),
                "phase": c.get("phase", ""),
                "roas": c.get("roas", 0.0),
                "spend": c.get("spend", 0.0),
                "status": c.get("status", ""),
            },
            "replay_hash": c.get("replay_hash"),
            "sequence_id": c.get("sequence_id"),
        })
    return index_batch(items, collection=COLLECTION_CAMPAIGNS, source_type="campaign")


def recall_campaigns(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    product: str | None = None,
    phase: str | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Retrieve semantically similar campaigns for *query*."""
    filters: dict[str, Any] = {}
    if product:
        filters["product"] = product
    if phase:
        filters["phase"] = phase
    return semantic_search(
        SearchQuery(
            collection=COLLECTION_CAMPAIGNS,
            query_text=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )
