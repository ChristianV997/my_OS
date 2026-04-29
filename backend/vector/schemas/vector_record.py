"""VectorRecord — the atomic unit of vector storage with full lineage metadata."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing      import Any


@dataclass
class VectorRecord:
    """A single embedded document ready for upsert into a vector collection.

    ``record_id`` should be a deterministic UUID5 derived from
    ``f"{source}:{key}"`` so repeated indexing of the same content is
    idempotent (upsert semantics).
    """
    record_id:  str                        # UUID5 deterministic ID
    vector:     list[float]                # embedding (384-dim default)
    payload:    dict[str, Any]             # arbitrary metadata / lineage
    collection: str = ""                   # target collection name
    source:     str = ""                   # producing system (e.g. "creative", "signal")
    sequence_id: str = ""                  # links to inference.sequence_id chain

    # ── convenience ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":   self.record_id,
            "vector":      self.vector,
            "payload":     self.payload,
            "collection":  self.collection,
            "source":      self.source,
            "sequence_id": self.sequence_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VectorRecord":
        return cls(
            record_id=d["record_id"],
            vector=d["vector"],
            payload=d.get("payload", {}),
            collection=d.get("collection", ""),
            source=d.get("source", ""),
            sequence_id=d.get("sequence_id", ""),
        )
