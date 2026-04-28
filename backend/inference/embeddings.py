"""backend.inference.embeddings — embedding pipeline with caching and telemetry.

Provides a high-level embedding API layered on top of the InferenceRouter.

Features
--------
- Provider abstraction: any provider with supports_embeddings=True is eligible
- Deterministic embeddings: same input → same output (when using deterministic providers)
- Caching hooks: an in-process LRU cache keyed by (model, text) replay hash
- Telemetry: all calls emit inference.embed events via telemetry.py

Usage
-----
    from backend.inference.embeddings import embed_texts

    vectors = embed_texts(["hello world", "foo bar"])
    # vectors: list[list[float]], one vector per input text
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from typing import Any

_log = logging.getLogger(__name__)

# ── in-process LRU cache ──────────────────────────────────────────────────────

_CACHE_MAX = 512  # max number of (model, text) cache entries


@functools.lru_cache(maxsize=_CACHE_MAX)
def _cached_single_embed(
    model: str,
    provider: str,
    text: str,
) -> tuple[float, ...]:
    """Cache wrapper for a single text embedding.  Returns a tuple (hashable)."""
    from backend.inference.models.embedding_request import EmbeddingRequest
    from backend.inference.router import inference_router

    req = EmbeddingRequest(texts=[text], model=model, provider=provider)
    resp = inference_router.embed(req)
    if resp.ok and resp.embeddings:
        return tuple(resp.embeddings[0])
    return ()


def embed_texts(
    texts: list[str],
    model: str = "default",
    provider: str = "auto",
    use_cache: bool = True,
    sequence_id: int | None = None,
    correlation_id: str | None = None,
) -> list[list[float]]:
    """Embed a list of texts and return one float vector per text.

    Parameters
    ----------
    texts : list[str]
        Input strings to embed.
    model : str
        Embedding model identifier.  "default" lets the provider decide.
    provider : str
        Provider hint.  "auto" lets the routing policy decide.
    use_cache : bool
        If True, uses the in-process LRU cache (default: True).
        Disable for fresh embeddings in replay/validation scenarios.
    sequence_id : int | None
        Deterministic ordering key; passed through to telemetry.
    correlation_id : str | None
        Links this call to a parent request.

    Returns
    -------
    list[list[float]]
        One vector per input text.  Returns an empty list on failure.
    """
    if not texts:
        return []

    if use_cache:
        results = []
        for text in texts:
            vec = _cached_single_embed(model, provider, text)
            results.append(list(vec) if vec else [])
        return results

    # Uncached: batch the full request
    from backend.inference.models.embedding_request import EmbeddingRequest
    from backend.inference.router import inference_router

    req = EmbeddingRequest(
        texts=texts,
        model=model,
        provider=provider,
        sequence_id=sequence_id,
        correlation_id=correlation_id,
    )
    resp = inference_router.embed(req)
    if resp.ok:
        return resp.embeddings
    _log.warning("embed_texts_failed error=%s", resp.error)
    return []


def embed_text(
    text: str,
    model: str = "default",
    provider: str = "auto",
    use_cache: bool = True,
) -> list[float]:
    """Embed a single text string.  Convenience wrapper around embed_texts."""
    results = embed_texts([text], model=model, provider=provider, use_cache=use_cache)
    return results[0] if results else []


def embedding_replay_hash(
    texts: list[str],
    model: str = "default",
    provider: str = "auto",
) -> str:
    """Compute a deterministic hash for an embedding request (for cache keying)."""
    canonical = {"model": model, "provider": provider, "texts": sorted(texts)}
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()


def clear_embedding_cache() -> None:
    """Clear the in-process LRU embedding cache."""
    _cached_single_embed.cache_clear()
