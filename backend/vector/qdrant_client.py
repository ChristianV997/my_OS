"""backend.vector.qdrant_client — Qdrant-backed store with in-memory fallback.

On import the module tries to connect to Qdrant at
``QDRANT_HOST:QDRANT_PORT`` (defaults: localhost:6333).  If the import
of ``qdrant_client`` fails (package not installed) or the server is
unreachable, an ``InMemoryVectorStore`` is used transparently.

Public surface:
    get_store() -> VectorStore (singleton)
    VectorStore  — abstract-ish base interface
    InMemoryVectorStore
    QdrantVectorStore
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from .schemas           import VectorRecord, SearchQuery, SimilarityResult
from .collections       import CollectionSpec, get_spec, ALL_COLLECTIONS
from .normalization      import normalize

log = logging.getLogger(__name__)

_QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
_QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# ── abstract interface ────────────────────────────────────────────────────────


class VectorStore:
    """Minimal protocol every backend must satisfy."""

    def ensure_collection(self, spec: CollectionSpec) -> None:
        raise NotImplementedError

    def upsert(self, records: list[VectorRecord]) -> int:
        """Return count of records upserted."""
        raise NotImplementedError

    def search(self, query: SearchQuery) -> list[SimilarityResult]:
        raise NotImplementedError

    def delete(self, collection: str, record_ids: list[str]) -> int:
        raise NotImplementedError

    def count(self, collection: str) -> int:
        raise NotImplementedError

    def collections(self) -> list[str]:
        raise NotImplementedError

    @property
    def backend_name(self) -> str:
        raise NotImplementedError


# ── in-memory fallback ────────────────────────────────────────────────────────


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot  = sum(x * y for x, y in zip(a, b))
    na   = sum(x * x for x in a) ** 0.5
    nb   = sum(x * x for x in b) ** 0.5
    denom = na * nb
    return dot / denom if denom > 1e-12 else 0.0


class InMemoryVectorStore(VectorStore):
    """Thread-safe in-memory vector store for dev / test without Docker."""

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        # collection → {record_id: (vector, payload)}
        self._data: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    def ensure_collection(self, spec: CollectionSpec) -> None:
        with self._lock:
            self._data.setdefault(spec.name, {})

    def upsert(self, records: list[VectorRecord]) -> int:
        count = 0
        with self._lock:
            for r in records:
                col = self._data.setdefault(r.collection, {})
                col[r.record_id] = (r.vector, r.payload)
                count += 1
        return count

    def search(self, query: SearchQuery) -> list[SimilarityResult]:
        with self._lock:
            col = self._data.get(query.collection, {})
            if not col:
                return []
            scores: list[SimilarityResult] = []
            for rid, (vec, payload) in col.items():
                score = _cosine(query.vector, vec)
                if score >= query.score_threshold:
                    scores.append(SimilarityResult(
                        record_id=rid,
                        score=score,
                        payload=payload if query.include_payload else {},
                        collection=query.collection,
                    ))
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[: query.top_k]

    def delete(self, collection: str, record_ids: list[str]) -> int:
        removed = 0
        with self._lock:
            col = self._data.get(collection, {})
            for rid in record_ids:
                if rid in col:
                    del col[rid]
                    removed += 1
        return removed

    def count(self, collection: str) -> int:
        with self._lock:
            return len(self._data.get(collection, {}))

    def collections(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    @property
    def backend_name(self) -> str:
        return "memory"


# ── Qdrant-backed store ───────────────────────────────────────────────────────


class QdrantVectorStore(VectorStore):
    """Wraps the official ``qdrant_client`` SDK."""

    def __init__(self, host: str = _QDRANT_HOST, port: int = _QDRANT_PORT) -> None:
        from qdrant_client import QdrantClient  # type: ignore[import]
        from qdrant_client.models import (  # type: ignore[import]
            Distance, VectorParams, PointStruct,
        )
        self._QdrantClient  = QdrantClient
        self._Distance      = Distance
        self._VectorParams  = VectorParams
        self._PointStruct   = PointStruct
        self._client        = QdrantClient(host=host, port=port, timeout=5)
        log.info("QdrantVectorStore connected at %s:%s", host, port)

    def ensure_collection(self, spec: CollectionSpec) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if spec.name not in existing:
            dist = getattr(self._Distance, spec.distance.upper(), self._Distance.COSINE)
            self._client.create_collection(
                collection_name=spec.name,
                vectors_config=self._VectorParams(size=spec.vector_size, distance=dist),
            )
            log.info("Created Qdrant collection %r", spec.name)

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0
        # Group by collection
        by_col: dict[str, list[VectorRecord]] = {}
        for r in records:
            by_col.setdefault(r.collection, []).append(r)
        total = 0
        for col, recs in by_col.items():
            points = [
                self._PointStruct(id=r.record_id, vector=r.vector, payload=r.payload)
                for r in recs
            ]
            self._client.upsert(collection_name=col, points=points, wait=True)
            total += len(recs)
        return total

    def search(self, query: SearchQuery) -> list[SimilarityResult]:
        hits = self._client.search(
            collection_name=query.collection,
            query_vector=query.vector,
            limit=query.top_k,
            score_threshold=query.score_threshold if query.score_threshold > 0 else None,
            with_payload=query.include_payload,
            query_filter=query.filter or None,
        )
        return [
            SimilarityResult(
                record_id=str(h.id),
                score=float(h.score),
                payload=h.payload or {},
                collection=query.collection,
            )
            for h in hits
        ]

    def delete(self, collection: str, record_ids: list[str]) -> int:
        from qdrant_client.models import PointIdsList  # type: ignore[import]
        self._client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=record_ids),
        )
        return len(record_ids)

    def count(self, collection: str) -> int:
        try:
            return self._client.count(collection_name=collection).count
        except Exception:
            return 0

    def collections(self) -> list[str]:
        return [c.name for c in self._client.get_collections().collections]

    @property
    def backend_name(self) -> str:
        return "qdrant"


# ── singleton factory ─────────────────────────────────────────────────────────

_store_instance: VectorStore | None = None
_store_lock = threading.Lock()


def _build_store() -> VectorStore:
    try:
        store = QdrantVectorStore()
        # Ensure all canonical collections exist
        for name in ALL_COLLECTIONS:
            store.ensure_collection(get_spec(name))
        return store
    except Exception as exc:
        log.warning("Qdrant unavailable (%s) — falling back to InMemoryVectorStore", exc)
        store = InMemoryVectorStore()
        for name in ALL_COLLECTIONS:
            store.ensure_collection(get_spec(name))
        return store


def get_store() -> VectorStore:
    """Return the module-level singleton VectorStore (Qdrant or in-memory)."""
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = _build_store()
    return _store_instance


def reset_store(store: VectorStore | None = None) -> None:
    """Replace the singleton — used by tests to inject a fresh in-memory store."""
    global _store_instance
    with _store_lock:
        _store_instance = store
