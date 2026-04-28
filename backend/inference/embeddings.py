"""High-level embedding API — the interface Phase 3 (Vector Cognition) will consume.

All embedding requests go through the InferenceRouter so provider selection,
fallback, and telemetry are handled automatically.

Designed for Phase 3 (backend/vector/) to call without knowing which provider
is active.  The router resolves provider priority and caches results.

Usage:
    from backend.inference.embeddings import embed_hooks, embed_products

    hook_vecs = embed_hooks(["This changed everything…", "Stop wasting money"])
    # → {"This changed everything…": [0.12, -0.34, ...], ...}
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from ._utils import now_ms
from .models.embedding_request import EmbeddingRequest

_log = logging.getLogger(__name__)

# Shared embedding dimension (mock=384, OpenAI text-embedding-3-small=1536)
# Phase 3 reads this to size Qdrant collections.
DEFAULT_EMBED_DIM = 384


# ── core helpers ──────────────────────────────────────────────────────────────

def embed_text(text: str, **kwargs) -> list[float]:
    """Embed a single string.  Returns a normalised float vector."""
    vecs = embed_batch([text], **kwargs)
    return vecs[0] if vecs else []


def embed_batch(texts: list[str], normalize: bool = True, **kwargs) -> list[list[float]]:
    """Embed a list of strings.  Returns one vector per input string."""
    if not texts:
        return []
    from .router import get_router
    t0  = now_ms()
    req = EmbeddingRequest(texts=texts, normalize=normalize, **kwargs)
    vecs = get_router().embed(req)
    _log.debug("embed_batch count=%d latency_ms=%.1f", len(texts), now_ms() - t0)
    return vecs


# ── domain-specific helpers (Phase 3 consumers) ───────────────────────────────

def embed_hooks(hooks: list[str]) -> dict[str, list[float]]:
    """Embed creative hooks.  Returns {hook_text: vector}."""
    if not hooks:
        return {}
    vecs = embed_batch(hooks)
    return {hook: vec for hook, vec in zip(hooks, vecs)}


def embed_products(products: list[str]) -> dict[str, list[float]]:
    """Embed product names / descriptions.  Returns {product: vector}."""
    if not products:
        return {}
    vecs = embed_batch(products)
    return {prod: vec for prod, vec in zip(products, vecs)}


def embed_campaigns(campaign_descriptors: list[str]) -> dict[str, list[float]]:
    """Embed campaign description strings for similarity search."""
    if not campaign_descriptors:
        return {}
    vecs = embed_batch(campaign_descriptors)
    return {desc: vec for desc, vec in zip(campaign_descriptors, vecs)}


def embed_angles(angles: list[str]) -> dict[str, list[float]]:
    """Embed creative angles (social-proof, urgency, problem-solution…)."""
    if not angles:
        return {}
    vecs = embed_batch(angles)
    return {angle: vec for angle, vec in zip(angles, vecs)}


def similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two pre-normalised vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def top_k_similar(
    query_vec:  list[float],
    candidates: dict[str, list[float]],
    k:          int = 5,
) -> list[tuple[str, float]]:
    """Return top-k candidates by cosine similarity to query_vec."""
    scored = [(name, similarity(query_vec, vec)) for name, vec in candidates.items()]
    return sorted(scored, key=lambda x: -x[1])[:k]
