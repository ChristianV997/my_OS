"""backend.vector.embeddings — cached embedding wrapper over inference.embeddings.

Adds an LRU in-memory cache so repeated embeds of the same text don't
round-trip through the inference kernel on every call.
"""
from __future__ import annotations

import functools
import threading
from typing import Any

from .normalization import normalize as _normalize

_CACHE: dict[str, list[float]] = {}
_CACHE_LOCK = threading.Lock()
_MAX_CACHE  = int(__import__("os").getenv("VECTOR_EMBED_CACHE_SIZE", "4096"))


def _cache_get(key: str) -> list[float] | None:
    with _CACHE_LOCK:
        return _CACHE.get(key)


def _cache_set(key: str, vec: list[float]) -> None:
    with _CACHE_LOCK:
        if len(_CACHE) >= _MAX_CACHE:
            # Evict oldest inserted key (insertion order in Python 3.7+)
            oldest = next(iter(_CACHE))
            del _CACHE[oldest]
        _CACHE[key] = vec


def embed_text(text: str, normalize: bool = True) -> list[float]:
    """Embed a single text string; results are cached by text content."""
    cached = _cache_get(text)
    if cached is not None:
        return cached
    from backend.inference.embeddings import embed_text as _embed
    vec = _embed(text)
    if normalize:
        vec = _normalize(vec)
    _cache_set(text, vec)
    return vec


def embed_batch(texts: list[str], normalize: bool = True) -> list[list[float]]:
    """Embed multiple texts, using the cache for any already-seen strings."""
    if not texts:
        return []

    # Identify which are cache misses
    results: list[list[float] | None] = [_cache_get(t) for t in texts]
    miss_indices = [i for i, r in enumerate(results) if r is None]
    miss_texts   = [texts[i] for i in miss_indices]

    if miss_texts:
        from backend.inference.embeddings import embed_batch as _batch
        fresh = _batch(miss_texts)
        if normalize:
            fresh = [_normalize(v) for v in fresh]
        for idx, vec in zip(miss_indices, fresh):
            _cache_set(texts[idx], vec)
            results[idx] = vec

    return [r for r in results if r is not None]


def embed_dict(items: dict[str, Any], normalize: bool = True) -> dict[str, list[float]]:
    """Embed keys of *items* dict. Values are ignored; useful for hook maps."""
    texts = list(items.keys())
    vecs  = embed_batch(texts, normalize=normalize)
    return dict(zip(texts, vecs))


def cache_size() -> int:
    with _CACHE_LOCK:
        return len(_CACHE)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
