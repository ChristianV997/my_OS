"""backend.vector.schemas.vector_record — canonical vector record schema.

Every record stored in the vector index carries deterministic lineage
fields so it can be replayed, audited, and correlated back to the
originating runtime event.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """A single indexed vector with full deterministic lineage.

    Fields
    ------
    record_id       — unique identifier for this vector record
    collection      — Qdrant collection name (e.g. "signals", "creatives")
    source_id       — ID of the originating document / event
    source_type     — logical category: "signal", "creative", "campaign",
                      "research", "trace", "telemetry"
    vector          — float embedding vector
    payload         — arbitrary metadata stored alongside the vector
    replay_hash     — sha256 of canonical content; ensures idempotent indexing
    sequence_id     — deterministic ordering key from the originating event
    embedding_model — embedding model used to produce this vector
    embedding_provider — inference provider used to produce this vector
    ts              — creation timestamp (unix float)
    """

    collection: str
    source_id: str
    source_type: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    replay_hash: str | None = None
    sequence_id: int | None = None
    embedding_model: str = "default"
    embedding_provider: str = "auto"
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.replay_hash:
            self.replay_hash = self._compute_replay_hash()

    def _compute_replay_hash(self) -> str:
        canonical = {
            "collection": self.collection,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "embedding_model": self.embedding_model,
            "embedding_provider": self.embedding_provider,
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "collection": self.collection,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "vector": self.vector,
            "payload": self.payload,
            "replay_hash": self.replay_hash,
            "sequence_id": self.sequence_id,
            "embedding_model": self.embedding_model,
            "embedding_provider": self.embedding_provider,
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorRecord":
        return cls(
            record_id=data.get("record_id", uuid.uuid4().hex),
            collection=data["collection"],
            source_id=data["source_id"],
            source_type=data["source_type"],
            vector=data.get("vector", []),
            payload=data.get("payload", {}),
            replay_hash=data.get("replay_hash"),
            sequence_id=data.get("sequence_id"),
            embedding_model=data.get("embedding_model", "default"),
            embedding_provider=data.get("embedding_provider", "auto"),
            ts=data.get("ts", time.time()),
        )
