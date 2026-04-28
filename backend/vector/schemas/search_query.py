"""backend.vector.schemas.search_query — canonical search request schema."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchQuery:
    """A semantic search request against a vector collection.

    Fields
    ------
    collection      — target Qdrant collection
    query_text      — raw text to embed and search against (may be None if
                      query_vector is provided directly)
    query_vector    — pre-computed query vector (used when query_text is None)
    top_k           — number of results to return
    score_threshold — minimum cosine similarity (0.0 = no filter)
    filters         — optional metadata filters applied server-side
    source_types    — restrict results to specific source types
    replay_hash     — deterministic hash of this query for telemetry lineage
    sequence_id     — ordering key for replay correlation
    correlation_id  — links this search to a parent request
    request_id      — unique identifier for this search request
    ts              — request timestamp (unix float)
    """

    collection: str
    query_text: str | None = None
    query_vector: list[float] | None = None
    top_k: int = 10
    score_threshold: float = 0.0
    filters: dict[str, Any] = field(default_factory=dict)
    source_types: list[str] = field(default_factory=list)
    replay_hash: str | None = None
    sequence_id: int | None = None
    correlation_id: str | None = None
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.replay_hash:
            self.replay_hash = self._compute_replay_hash()

    def _compute_replay_hash(self) -> str:
        canonical = {
            "collection": self.collection,
            "query_text": self.query_text,
            "top_k": self.top_k,
            "score_threshold": self.score_threshold,
            "source_types": sorted(self.source_types),
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "collection": self.collection,
            "query_text": self.query_text,
            "top_k": self.top_k,
            "score_threshold": self.score_threshold,
            "filters": self.filters,
            "source_types": self.source_types,
            "replay_hash": self.replay_hash,
            "sequence_id": self.sequence_id,
            "correlation_id": self.correlation_id,
            "ts": self.ts,
        }
