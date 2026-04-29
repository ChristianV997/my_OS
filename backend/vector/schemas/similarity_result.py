"""SimilarityResult — one hit returned by semantic search."""
from __future__ import annotations
from dataclasses import dataclass
from typing      import Any


@dataclass
class SimilarityResult:
    """A single ranked result from vector similarity search."""
    record_id: str
    score:     float
    payload:   dict[str, Any]
    collection: str = ""

    # ── ordering support ──────────────────────────────────────────────────────

    def __lt__(self, other: "SimilarityResult") -> bool:
        return self.score < other.score

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SimilarityResult):
            return NotImplemented
        return self.record_id == other.record_id
