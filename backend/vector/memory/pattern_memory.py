"""backend.vector.memory.pattern_memory — semantic memory for patterns.

Indexes pattern-store entries (orchestration patterns, winning genome
configurations, structural evolution outcomes) and provides semantic
retrieval to surface relevant past patterns during decision-making.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_PATTERNS
from backend.vector.indexing import index_record, index_batch
from backend.vector.schemas.search_query import SearchQuery
from backend.vector.semantic_search import semantic_search
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_pattern(
    source_id: str,
    text: str,
    pattern_type: str = "execution",
    score: float = 0.0,
    phase: str = "",
    extra: dict[str, Any] | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Index an operational pattern into the patterns collection.

    Parameters
    ----------
    source_id    — unique pattern identifier
    text         — textual description of the pattern
    pattern_type — "execution", "genome", "regime", "structural"
    score        — pattern performance score
    phase        — runtime phase where pattern was observed
    """
    payload: dict[str, Any] = {
        "pattern_type": pattern_type,
        "score": score,
        "phase": phase,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_PATTERNS,
        source_id=source_id,
        source_type="pattern",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )


def index_patterns_batch(patterns: list[dict[str, Any]]) -> int:
    """Index a batch of pattern dicts."""
    items = []
    for p in patterns:
        text = p.get("description") or p.get("text") or p.get("name", "")
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": p.get("id", p.get("pattern_id", "")),
            "payload": {
                "pattern_type": p.get("pattern_type", "execution"),
                "score": p.get("score", 0.0),
                "phase": p.get("phase", ""),
            },
            "replay_hash": p.get("replay_hash"),
            "sequence_id": p.get("sequence_id"),
        })
    return index_batch(items, collection=COLLECTION_PATTERNS, source_type="pattern")


def recall_patterns(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    pattern_type: str | None = None,
    phase: str | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Retrieve semantically similar patterns for *query*."""
    filters: dict[str, Any] = {}
    if pattern_type:
        filters["pattern_type"] = pattern_type
    if phase:
        filters["phase"] = phase
    return semantic_search(
        SearchQuery(
            collection=COLLECTION_PATTERNS,
            query_text=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )
