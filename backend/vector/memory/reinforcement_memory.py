"""backend.vector.memory.reinforcement_memory — semantic reinforcement memory.

Indexes successful execution traces, calibration outcomes, and winning
creative patterns to enable semantic reinforcement retrieval: given a
new execution context, retrieve the most relevant past successes.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_REINFORCEMENT
from backend.vector.indexing import index_record, index_batch
from backend.vector.schemas.search_query import SearchQuery
from backend.vector.semantic_search import semantic_search
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_reinforcement(
    source_id: str,
    text: str,
    outcome: str = "",
    reward: float = 0.0,
    phase: str = "",
    trace_type: str = "execution",
    extra: dict[str, Any] | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Index a reinforcement outcome into the reinforcement collection.

    Parameters
    ----------
    source_id  — unique trace / outcome identifier
    text       — textual description of the execution context
    outcome    — "success", "failure", "neutral"
    reward     — numeric reward signal
    phase      — runtime phase
    trace_type — "execution", "calibration", "deployment", "pattern"
    """
    payload: dict[str, Any] = {
        "outcome": outcome,
        "reward": reward,
        "phase": phase,
        "trace_type": trace_type,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_REINFORCEMENT,
        source_id=source_id,
        source_type="reinforcement",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )


def index_reinforcement_batch(outcomes: list[dict[str, Any]]) -> int:
    """Index a batch of reinforcement outcomes."""
    items = []
    for o in outcomes:
        text = o.get("text") or o.get("context") or o.get("description", "")
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": o.get("id", o.get("source_id", "")),
            "payload": {
                "outcome": o.get("outcome", ""),
                "reward": o.get("reward", 0.0),
                "phase": o.get("phase", ""),
                "trace_type": o.get("trace_type", "execution"),
            },
            "replay_hash": o.get("replay_hash"),
            "sequence_id": o.get("sequence_id"),
        })
    return index_batch(items, collection=COLLECTION_REINFORCEMENT, source_type="reinforcement")


def recall_reinforcement(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    outcome: str | None = None,
    phase: str | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Retrieve semantically similar reinforcement outcomes for *query*."""
    filters: dict[str, Any] = {}
    if outcome:
        filters["outcome"] = outcome
    if phase:
        filters["phase"] = phase
    return semantic_search(
        SearchQuery(
            collection=COLLECTION_REINFORCEMENT,
            query_text=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )


def recall_successes(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Recall successful execution traces most similar to *query*."""
    return recall_reinforcement(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        outcome="success",
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )
