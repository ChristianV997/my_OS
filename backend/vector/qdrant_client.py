"""backend.vector.qdrant_client — deterministic Qdrant collection management.

Provides a thin, replay-safe wrapper around the Qdrant client library.
When Qdrant is unavailable the client degrades gracefully: all writes
are no-ops and all searches return empty results so the rest of the
stack (telemetry, replay, embeddings) continues working.

Design
------
- Collections are created deterministically: same name → same config.
- Records are upserted by ``record_id`` (idempotent).
- All public methods accept ``replay_hash`` / ``sequence_id`` so callers
  can carry deterministic lineage through every operation.
- Telemetry is emitted for every index and search operation via
  ``backend.vector.telemetry``.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from backend.vector.schemas.vector_record import VectorRecord
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector import telemetry as vt

_log = logging.getLogger(__name__)

# ── well-known collection names ───────────────────────────────────────────────

COLLECTION_SIGNALS      = "signals"
COLLECTION_CREATIVES    = "creatives"
COLLECTION_CAMPAIGNS    = "campaigns"
COLLECTION_RESEARCH     = "research"
COLLECTION_TRACES       = "traces"
COLLECTION_TELEMETRY    = "telemetry"
COLLECTION_PATTERNS     = "patterns"
COLLECTION_REINFORCEMENT = "reinforcement"

# Default vector dimension — overridden at collection creation if known.
_DEFAULT_DIM = 384


def _try_import_qdrant():
    """Return (QdrantClient, models) or (None, None) if not installed."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client import models as qdrant_models
        return QdrantClient, qdrant_models
    except ImportError:
        return None, None


class VectorStoreClient:
    """Replay-safe Qdrant wrapper with graceful degradation.

    Parameters
    ----------
    host    — Qdrant host (default "localhost")
    port    — Qdrant gRPC port (default 6333)
    url     — Full URL override; takes precedence over host/port
    in_memory — Use an in-memory Qdrant instance (useful for tests)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        url: str | None = None,
        in_memory: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._url = url
        self._in_memory = in_memory
        self._client: Any = None
        self._models: Any = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        QdrantClient, models = _try_import_qdrant()
        if QdrantClient is None:
            _log.info("qdrant_client_not_installed degrading_gracefully=True")
            return
        try:
            if self._in_memory:
                self._client = QdrantClient(":memory:")
            elif self._url:
                self._client = QdrantClient(url=self._url)
            else:
                self._client = QdrantClient(host=self._host, port=self._port)
            self._models = models
            self._available = True
            _log.info("qdrant_connected host=%s port=%s", self._host, self._port)
        except Exception as exc:
            _log.warning("qdrant_connect_failed error=%s degrading=True", exc)

    @property
    def available(self) -> bool:
        return self._available

    # ── collection management ─────────────────────────────────────────────────

    def ensure_collection(
        self,
        name: str,
        vector_dim: int = _DEFAULT_DIM,
        distance: str = "Cosine",
    ) -> bool:
        """Ensure a collection exists with the given config.

        Idempotent — safe to call on every startup.  Returns True on success.
        """
        if not self._available:
            return False
        try:
            existing = [c.name for c in self._client.get_collections().collections]
            if name not in existing:
                dist = getattr(self._models.Distance, distance.upper(), self._models.Distance.COSINE)
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=self._models.VectorParams(
                        size=vector_dim,
                        distance=dist,
                    ),
                )
                _log.info("collection_created name=%s dim=%s", name, vector_dim)
            return True
        except Exception as exc:
            _log.warning("ensure_collection_failed name=%s error=%s", name, exc)
            return False

    def delete_collection(self, name: str) -> bool:
        """Delete a collection. Returns True on success."""
        if not self._available:
            return False
        try:
            self._client.delete_collection(name)
            return True
        except Exception as exc:
            _log.warning("delete_collection_failed name=%s error=%s", name, exc)
            return False

    def collection_exists(self, name: str) -> bool:
        """Return True if the collection exists."""
        if not self._available:
            return False
        try:
            names = [c.name for c in self._client.get_collections().collections]
            return name in names
        except Exception:
            return False

    # ── upsert / index ────────────────────────────────────────────────────────

    def upsert(self, record: VectorRecord) -> bool:
        """Index a VectorRecord into its collection.

        Uses ``record.record_id`` as the Qdrant point ID, making every
        upsert idempotent.  Returns True on success.
        """
        t0 = time.time()
        if not self._available:
            vt.emit_index_error(
                collection=record.collection,
                source_id=record.source_id,
                error="qdrant_unavailable",
                replay_hash=record.replay_hash,
                sequence_id=record.sequence_id,
            )
            return False
        try:
            self.ensure_collection(record.collection, vector_dim=len(record.vector) or _DEFAULT_DIM)
            payload = {
                **record.payload,
                "_source_id": record.source_id,
                "_source_type": record.source_type,
                "_replay_hash": record.replay_hash,
                "_sequence_id": record.sequence_id,
                "_embedding_model": record.embedding_model,
                "_embedding_provider": record.embedding_provider,
                "_ts": record.ts,
            }
            # Qdrant point IDs must be unsigned int or UUID string
            point_id = str(uuid.UUID(record.record_id)) if len(record.record_id) == 32 else str(uuid.uuid5(uuid.NAMESPACE_DNS, record.record_id))
            self._client.upsert(
                collection_name=record.collection,
                points=[
                    self._models.PointStruct(
                        id=point_id,
                        vector=record.vector,
                        payload=payload,
                    )
                ],
            )
            latency_ms = (time.time() - t0) * 1000
            vt.emit_index(
                collection=record.collection,
                record_id=record.record_id,
                source_id=record.source_id,
                source_type=record.source_type,
                replay_hash=record.replay_hash,
                sequence_id=record.sequence_id,
                embedding_model=record.embedding_model,
                embedding_provider=record.embedding_provider,
                latency_ms=latency_ms,
                vector_dim=len(record.vector),
            )
            return True
        except Exception as exc:
            _log.warning("upsert_failed collection=%s source=%s error=%s", record.collection, record.source_id, exc)
            vt.emit_index_error(
                collection=record.collection,
                source_id=record.source_id,
                error=str(exc),
                replay_hash=record.replay_hash,
                sequence_id=record.sequence_id,
            )
            return False

    def upsert_batch(self, records: list[VectorRecord]) -> int:
        """Upsert a batch of VectorRecords. Returns count of successes."""
        return sum(1 for r in records if self.upsert(r))

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
        replay_hash: str | None = None,
        sequence_id: int | None = None,
        request_id: str | None = None,
    ) -> list[SimilarityResult]:
        """Perform a top-k nearest-neighbour search.

        Returns a list of SimilarityResult sorted by score descending.
        Returns empty list when Qdrant is unavailable.
        """
        t0 = time.time()
        req_id = request_id or uuid.uuid4().hex[:12]
        if not self._available:
            vt.emit_search_error(
                collection=collection,
                request_id=req_id,
                error="qdrant_unavailable",
                replay_hash=replay_hash,
                sequence_id=sequence_id,
            )
            return []
        try:
            qdrant_filter = None
            if filters:
                must_conditions = []
                for key, value in filters.items():
                    must_conditions.append(
                        self._models.FieldCondition(
                            key=key,
                            match=self._models.MatchValue(value=value),
                        )
                    )
                if must_conditions:
                    qdrant_filter = self._models.Filter(must=must_conditions)

            hits = self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold if score_threshold > 0.0 else None,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            results: list[SimilarityResult] = []
            for rank, hit in enumerate(hits, start=1):
                payload = hit.payload or {}
                results.append(
                    SimilarityResult(
                        record_id=str(hit.id),
                        score=float(hit.score),
                        source_id=payload.get("_source_id", ""),
                        source_type=payload.get("_source_type", ""),
                        collection=collection,
                        payload={k: v for k, v in payload.items() if not k.startswith("_")},
                        replay_hash=payload.get("_replay_hash"),
                        sequence_id=payload.get("_sequence_id"),
                        rank=rank,
                    )
                )
            latency_ms = (time.time() - t0) * 1000
            vt.emit_search(
                collection=collection,
                request_id=req_id,
                top_k=top_k,
                result_count=len(results),
                latency_ms=latency_ms,
                replay_hash=replay_hash,
                sequence_id=sequence_id,
                score_threshold=score_threshold,
            )
            return results
        except Exception as exc:
            _log.warning("search_failed collection=%s error=%s", collection, exc)
            vt.emit_search_error(
                collection=collection,
                request_id=req_id,
                error=str(exc),
                replay_hash=replay_hash,
                sequence_id=sequence_id,
            )
            return []

    def count(self, collection: str) -> int:
        """Return the number of vectors in a collection. 0 on error."""
        if not self._available:
            return 0
        try:
            result = self._client.count(collection_name=collection, exact=True)
            return int(result.count)
        except Exception:
            return 0


# ── module-level singleton ────────────────────────────────────────────────────

_vector_store: VectorStoreClient | None = None


def get_vector_store(
    host: str = "localhost",
    port: int = 6333,
    url: str | None = None,
    in_memory: bool = False,
) -> VectorStoreClient:
    """Return the module-level VectorStoreClient singleton.

    The first call initialises the client; subsequent calls return the
    existing instance.  Pass ``in_memory=True`` in tests.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreClient(host=host, port=port, url=url, in_memory=in_memory)
    return _vector_store


def reset_vector_store() -> None:
    """Reset the singleton (for testing only)."""
    global _vector_store
    _vector_store = None
