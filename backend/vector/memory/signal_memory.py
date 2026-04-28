"""backend.vector.memory.signal_memory — semantic memory for market signals.

Indexes market signals (Reddit, YouTube, social payloads, trend
summaries) into the Qdrant signals collection and provides semantic
retrieval over them.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.vector.qdrant_client import COLLECTION_SIGNALS
from backend.vector.indexing import index_record, index_batch
from backend.vector.semantic_search import search_signals
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord

_log = logging.getLogger(__name__)


def index_signal(
    source_id: str,
    text: str,
    source: str,
    intent: str = "unknown",
    velocity: float = 0.0,
    confidence: float = 0.0,
    extra: dict[str, Any] | None = None,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> VectorRecord | None:
    """Index a market signal into the signals collection.

    Parameters
    ----------
    source_id  — unique signal identifier
    text       — text content to embed (topic / summary / raw)
    source     — signal origin ("reddit", "youtube", "tiktok", …)
    intent     — buy / research / compare / unknown
    velocity   — signal velocity score
    confidence — confidence score
    extra      — additional metadata
    """
    payload: dict[str, Any] = {
        "source": source,
        "intent": intent,
        "velocity": velocity,
        "confidence": confidence,
        **(extra or {}),
    }
    return index_record(
        text=text,
        collection=COLLECTION_SIGNALS,
        source_id=source_id,
        source_type="signal",
        payload=payload,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )


def index_signals_batch(signals: list[dict[str, Any]]) -> int:
    """Index a batch of signal dicts.

    Each dict should match the ``TrendRecordStore`` schema:
    id, topic, intent, velocity, confidence, source, raw, …
    """
    items = []
    for s in signals:
        text = s.get("topic") or str(s.get("raw", ""))
        if not text:
            continue
        items.append({
            "text": text,
            "source_id": s.get("id", ""),
            "payload": {
                "source": s.get("source", ""),
                "intent": s.get("intent", "unknown"),
                "velocity": s.get("velocity", 0.0),
                "confidence": s.get("confidence", 0.0),
            },
            "replay_hash": None,
            "sequence_id": None,
        })
    return index_batch(items, collection=COLLECTION_SIGNALS, source_type="signal")


def recall_signals(
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Retrieve semantically similar signals for *query*."""
    return search_signals(
        text=query,
        top_k=top_k,
        score_threshold=score_threshold,
        replay_hash=replay_hash,
        sequence_id=sequence_id,
    )
