"""backend.vector.telemetry — telemetry instrumentation for all vector operations.

All vector operations (indexing, search, similarity, clustering) emit
structured events through the existing PubSubBroker so they appear in:
  - the durable RuntimeReplayStore
  - the WebSocket event stream
  - the command center frontend

Event types emitted
--------------------
vector.index        — record indexed into a collection
vector.search       — semantic search executed
vector.similarity   — pairwise similarity computed
vector.cluster      — clustering operation completed
vector.index_error  — indexing failure
vector.search_error — search failure
"""
from __future__ import annotations

import logging
import time
from typing import Any

_log = logging.getLogger(__name__)

# ── event type constants ──────────────────────────────────────────────────────

VECTOR_INDEX       = "vector.index"
VECTOR_SEARCH      = "vector.search"
VECTOR_SIMILARITY  = "vector.similarity"
VECTOR_CLUSTER     = "vector.cluster"
VECTOR_INDEX_ERROR = "vector.index_error"
VECTOR_SEARCH_ERROR = "vector.search_error"


def _broker():
    try:
        from backend.pubsub.broker import broker as _b
        return _b
    except Exception:
        return None


def emit_index(
    collection: str,
    record_id: str,
    source_id: str,
    source_type: str,
    replay_hash: str | None,
    sequence_id: int | None,
    embedding_model: str,
    embedding_provider: str,
    latency_ms: float,
    vector_dim: int = 0,
) -> None:
    """Emit a vector.index event after a record is written to the index."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_INDEX,
            {
                "type": VECTOR_INDEX,
                "collection": collection,
                "record_id": record_id,
                "source_id": source_id,
                "source_type": source_type,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "embedding_model": embedding_model,
                "embedding_provider": embedding_provider,
                "vector_dim": vector_dim,
                "latency_ms": latency_ms,
                "ts": time.time(),
            },
            source="vector.indexing",
        )
    except Exception as exc:
        _log.warning("emit_index_failed error=%s", exc)


def emit_search(
    collection: str,
    request_id: str,
    top_k: int,
    result_count: int,
    latency_ms: float,
    replay_hash: str | None,
    sequence_id: int | None,
    score_threshold: float = 0.0,
    source_types: list[str] | None = None,
) -> None:
    """Emit a vector.search event after a semantic search completes."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_SEARCH,
            {
                "type": VECTOR_SEARCH,
                "collection": collection,
                "request_id": request_id,
                "top_k": top_k,
                "result_count": result_count,
                "score_threshold": score_threshold,
                "source_types": source_types or [],
                "latency_ms": latency_ms,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="vector.search",
        )
    except Exception as exc:
        _log.warning("emit_search_failed error=%s", exc)


def emit_similarity(
    collection: str,
    source_a: str,
    source_b: str,
    score: float,
    latency_ms: float,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit a vector.similarity event for a pairwise comparison."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_SIMILARITY,
            {
                "type": VECTOR_SIMILARITY,
                "collection": collection,
                "source_a": source_a,
                "source_b": source_b,
                "score": score,
                "latency_ms": latency_ms,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="vector.similarity",
        )
    except Exception as exc:
        _log.warning("emit_similarity_failed error=%s", exc)


def emit_cluster(
    collection: str,
    n_vectors: int,
    n_clusters: int,
    latency_ms: float,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit a vector.cluster event after a clustering operation."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_CLUSTER,
            {
                "type": VECTOR_CLUSTER,
                "collection": collection,
                "n_vectors": n_vectors,
                "n_clusters": n_clusters,
                "latency_ms": latency_ms,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="vector.clustering",
        )
    except Exception as exc:
        _log.warning("emit_cluster_failed error=%s", exc)


def emit_index_error(
    collection: str,
    source_id: str,
    error: str,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit a vector.index_error event on indexing failure."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_INDEX_ERROR,
            {
                "type": VECTOR_INDEX_ERROR,
                "collection": collection,
                "source_id": source_id,
                "error": error,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="vector.indexing",
        )
    except Exception as exc:
        _log.warning("emit_index_error_failed error=%s", exc)


def emit_search_error(
    collection: str,
    request_id: str,
    error: str,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> None:
    """Emit a vector.search_error event on search failure."""
    b = _broker()
    if b is None:
        return
    try:
        b.publish(
            VECTOR_SEARCH_ERROR,
            {
                "type": VECTOR_SEARCH_ERROR,
                "collection": collection,
                "request_id": request_id,
                "error": error,
                "replay_hash": replay_hash,
                "sequence_id": sequence_id,
                "ts": time.time(),
            },
            source="vector.search",
        )
    except Exception as exc:
        _log.warning("emit_search_error_failed error=%s", exc)
