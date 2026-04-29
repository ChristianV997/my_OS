"""ReplayBatch — a bounded window of events extracted for a consolidation pass."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReplayBatch:
    """A time-bounded slice of the event log for one consolidation window.

    The scheduler populates this from RuntimeReplayStore.recent() or
    EpisodicStore.window() before handing it to the ConsolidationEngine.
    All operations in a sleep cycle are derived from a single ReplayBatch
    to preserve temporal coherence.
    """
    batch_id:    str
    workspace:   str             = "default"
    start_ts:    float           = 0.0
    end_ts:      float           = 0.0
    events:      list[dict[str, Any]] = field(default_factory=list)
    source:      str             = "replay_store"  # replay_store | episodic

    @property
    def size(self) -> int:
        return len(self.events)

    @property
    def span_s(self) -> float:
        return max(0.0, self.end_ts - self.start_ts)

    def events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("type") == event_type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id":  self.batch_id,
            "workspace": self.workspace,
            "start_ts":  self.start_ts,
            "end_ts":    self.end_ts,
            "size":      self.size,
            "span_s":    self.span_s,
            "source":    self.source,
        }
