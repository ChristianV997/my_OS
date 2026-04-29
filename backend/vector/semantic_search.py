"""backend.vector.semantic_search — high-level semantic retrieval API."""
from __future__ import annotations

from typing import Any

from .qdrant_client import get_store
from .embeddings    import embed_text, embed_batch
from .schemas       import SearchQuery, SimilarityResult
from .collections   import (
    HOOKS, PRODUCTS, CAMPAIGNS, SIGNALS, PATTERNS, ANGLES, CREATIVES,
)


# ── single-collection search ──────────────────────────────────────────────────


def search(
    query_text: str,
    collection: str,
    top_k: int = 10,
    threshold: float = 0.0,
    filter: dict[str, Any] | None = None,
    sequence_id: str = "",
) -> list[SimilarityResult]:
    """Embed *query_text* and search *collection*."""
    vec   = embed_text(query_text)
    store = get_store()
    q = SearchQuery(
        vector=vec,
        collection=collection,
        top_k=top_k,
        score_threshold=threshold,
        filter=filter or {},
        sequence_id=sequence_id,
    )
    return store.search(q)


# ── multi-collection search ───────────────────────────────────────────────────


def search_all(
    query_text: str,
    top_k: int = 5,
    threshold: float = 0.0,
    collections: list[str] | None = None,
) -> dict[str, list[SimilarityResult]]:
    """Search *query_text* across multiple collections.

    Returns ``{collection_name: [SimilarityResult, ...]}``.
    """
    targets = collections or [HOOKS, PRODUCTS, SIGNALS, PATTERNS]
    vec     = embed_text(query_text)
    store   = get_store()
    results = {}
    for col in targets:
        q = SearchQuery(vector=vec, collection=col, top_k=top_k,
                        score_threshold=threshold)
        results[col] = store.search(q)
    return results


# ── domain-specific helpers ───────────────────────────────────────────────────


def find_similar_hooks(
    query: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(query, HOOKS, top_k=top_k, threshold=threshold)


def find_similar_products(
    query: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(query, PRODUCTS, top_k=top_k, threshold=threshold)


def find_similar_campaigns(
    query: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(query, CAMPAIGNS, top_k=top_k, threshold=threshold)


def find_similar_signals(
    query: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(query, SIGNALS, top_k=top_k, threshold=threshold)


def find_similar_patterns(
    query: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(query, PATTERNS, top_k=top_k, threshold=threshold)


def find_winning_angles(
    product: str,
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(product, ANGLES, top_k=top_k, threshold=threshold)


def find_creatives_by_hook(
    hook: str,
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[SimilarityResult]:
    return search(hook, CREATIVES, top_k=top_k, threshold=threshold)


# ── semantic ranking helper ───────────────────────────────────────────────────


def rank_by_similarity(
    query: str,
    texts: list[str],
) -> list[tuple[str, float]]:
    """Rank *texts* by cosine similarity to *query*. Returns (text, score) pairs."""
    from .similarity import cosine
    qvec  = embed_text(query)
    vecs  = embed_batch(texts)
    pairs = [(t, cosine(qvec, v)) for t, v in zip(texts, vecs)]
    return sorted(pairs, key=lambda x: x[1], reverse=True)
