"""backend.inference.models.embedding_request — canonical embedding request/response schemas."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmbeddingRequest:
    """Canonical schema for an embedding request.

    Fields
    ------
    texts           — one or more input strings to embed
    model           — embedding model identifier
    provider        — provider hint; "auto" lets policy decide
    request_id      — unique identifier; auto-generated if absent
    sequence_id     — deterministic ordering key
    replay_hash     — deterministic content hash; auto-computed if absent
    correlation_id  — links grouped requests
    ts              — creation timestamp
    extra           — provider-specific kwargs
    """

    texts: list[str]
    model: str = "default"
    provider: str = "auto"
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sequence_id: int | None = None
    replay_hash: str | None = None
    correlation_id: str | None = None
    ts: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.replay_hash:
            self.replay_hash = self._compute_replay_hash()

    def _compute_replay_hash(self) -> str:
        canonical = {"model": self.model, "provider": self.provider, "texts": self.texts}
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "texts": self.texts,
            "model": self.model,
            "provider": self.provider,
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "correlation_id": self.correlation_id,
            "ts": self.ts,
            "extra": self.extra,
        }


@dataclass
class EmbeddingResponse:
    """Canonical schema for an embedding response.

    Fields
    ------
    request_id      — mirrors EmbeddingRequest.request_id
    model           — actual model used
    provider        — actual provider used
    embeddings      — list of float vectors, one per input text
    latency_ms      — wall-clock latency in milliseconds
    sequence_id     — mirrors request
    replay_hash     — mirrors request
    ts              — response timestamp
    error           — None on success; error string on failure
    extra           — provider-specific metadata
    """

    request_id: str = ""
    model: str = ""
    provider: str = ""
    embeddings: list[list[float]] = field(default_factory=list)
    latency_ms: float = 0.0
    sequence_id: int | None = None
    replay_hash: str | None = None
    ts: float = field(default_factory=time.time)
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "embeddings": self.embeddings,
            "latency_ms": self.latency_ms,
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "ts": self.ts,
            "error": self.error,
            "extra": self.extra,
        }
