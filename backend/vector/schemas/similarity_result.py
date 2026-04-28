"""backend.vector.schemas.similarity_result — schema for a similarity search hit."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimilarityResult:
    """A single result from a semantic similarity search.

    Fields
    ------
    record_id   — ID of the matched VectorRecord
    score       — cosine similarity in [0, 1]; higher is more similar
    source_id   — originating document / event ID
    source_type — logical category of the matched record
    collection  — collection the record lives in
    payload     — metadata stored with the vector
    replay_hash — lineage hash of the matched record
    sequence_id — ordering key of the matched record
    rank        — 1-based rank within the result set
    ts          — timestamp of the search (unix float)
    """

    record_id: str
    score: float
    source_id: str
    source_type: str
    collection: str
    payload: dict[str, Any] = field(default_factory=dict)
    replay_hash: str | None = None
    sequence_id: int | None = None
    rank: int = 0
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "score": self.score,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "collection": self.collection,
            "payload": self.payload,
            "replay_hash": self.replay_hash,
            "sequence_id": self.sequence_id,
            "rank": self.rank,
            "ts": self.ts,
        }
