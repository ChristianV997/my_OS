"""backend.vector.semantic_search — high-level semantic retrieval API.

Provides a single ``semantic_search`` entry point that:
  1. Embeds the query text (reusing inference cache).
  2. Runs top-k search against the target Qdrant collection.
  3. Applies optional source-type filtering.
  4. Emits search telemetry.
  5. Returns ranked SimilarityResult objects with full lineage.

All operations are replay-safe: replay_hash / sequence_id flow through
every layer.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from backend.vector.schemas.search_query import SearchQuery
from backend.vector.schemas.similarity_result import SimilarityResult

_log = logging.getLogger(__name__)


def semantic_search(
    query: SearchQuery,
    embedding_model: str = "default",
    embedding_provider: str = "auto",
) -> list[SimilarityResult]:
    """Execute a semantic search described by *query*.

    Embedding is performed via the inference router if query_text is
    provided.  Pass query_vector directly to skip embedding.

    Returns ranked SimilarityResult list (may be empty on error or if
    Qdrant is unavailable).
    """
    from backend.vector.qdrant_client import get_vector_store
    from backend.vector.embeddings import embed_query

    t0 = time.time()

    # Resolve query vector
    query_vector = query.query_vector
    if query_vector is None:
        if not query.query_text:
            _log.warning("semantic_search_no_input collection=%s", query.collection)
            return []
        query_vector = embed_query(
            query.query_text,
            model=embedding_model,
            provider=embedding_provider,
        )
        if not query_vector:
            _log.warning("semantic_search_embed_failed collection=%s", query.collection)
            return []

    # Build metadata filter for source_types
    filters: dict[str, Any] = dict(query.filters)
    # source_types filtering is applied post-search (Qdrant filter on array
    # values requires MatchAny which varies across client versions)
    store = get_vector_store()
    results = store.search(
        collection=query.collection,
        query_vector=query_vector,
        top_k=query.top_k * 2 if query.source_types else query.top_k,
        score_threshold=query.score_threshold,
        filters=filters or None,
        replay_hash=query.replay_hash,
        sequence_id=query.sequence_id,
        request_id=query.request_id,
    )

    # Post-filter by source_type
    if query.source_types:
        results = [r for r in results if r.source_type in query.source_types]

    # Re-rank and trim to top_k
    results = results[: query.top_k]
    for i, r in enumerate(results, start=1):
        r.rank = i

    return results


def search_signals(
    text: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Semantic search over the signals collection."""
    from backend.vector.qdrant_client import COLLECTION_SIGNALS

    return semantic_search(
        SearchQuery(
            collection=COLLECTION_SIGNALS,
            query_text=text,
            top_k=top_k,
            score_threshold=score_threshold,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )


def search_creatives(
    text: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Semantic search over the creatives collection."""
    from backend.vector.qdrant_client import COLLECTION_CREATIVES

    return semantic_search(
        SearchQuery(
            collection=COLLECTION_CREATIVES,
            query_text=text,
            top_k=top_k,
            score_threshold=score_threshold,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )


def search_research(
    text: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Semantic search over the research collection."""
    from backend.vector.qdrant_client import COLLECTION_RESEARCH

    return semantic_search(
        SearchQuery(
            collection=COLLECTION_RESEARCH,
            query_text=text,
            top_k=top_k,
            score_threshold=score_threshold,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )


def search_reinforcement(
    text: str,
    top_k: int = 10,
    score_threshold: float = 0.0,
    replay_hash: str | None = None,
    sequence_id: int | None = None,
) -> list[SimilarityResult]:
    """Semantic search over the reinforcement collection."""
    from backend.vector.qdrant_client import COLLECTION_REINFORCEMENT

    return semantic_search(
        SearchQuery(
            collection=COLLECTION_REINFORCEMENT,
            query_text=text,
            top_k=top_k,
            score_threshold=score_threshold,
            replay_hash=replay_hash,
            sequence_id=sequence_id,
        )
    )
