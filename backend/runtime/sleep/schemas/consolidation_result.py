"""ConsolidationResult — output contract for one sleep cycle pass."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsolidationResult:
    """Immutable summary of one consolidation cycle execution.

    Written by ConsolidationEngine at the end of every sleep pass and
    emitted as a ``sleep.consolidation.completed`` event.  Consumers
    (dashboard, audit trail, next-cycle scheduler) read from the event
    log rather than the engine directly.
    """
    cycle_id:           str
    workspace:          str              = "default"
    started_at:         float            = field(default_factory=time.time)
    finished_at:        float            = 0.0
    episodes_read:      int              = 0
    episodes_compacted: int              = 0
    semantic_units_created: int          = 0
    semantic_units_pruned:  int          = 0
    procedures_reinforced:  int          = 0
    procedures_deprecated:  int          = 0
    lineage_nodes_summarized: int        = 0
    vectors_indexed:    int              = 0
    compression_ratio:  float            = 0.0
    decay_applied:      bool             = False
    errors:             list[str]        = field(default_factory=list)
    metadata:           dict[str, Any]   = field(default_factory=dict)

    def finish(self) -> None:
        self.finished_at = time.time()
        total_in  = max(self.episodes_read, 1)
        total_out = self.semantic_units_created + self.procedures_reinforced
        self.compression_ratio = round(total_out / total_in, 4) if total_in else 0.0

    @property
    def duration_s(self) -> float:
        if self.finished_at > 0:
            return self.finished_at - self.started_at
        return time.time() - self.started_at

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id":                 self.cycle_id,
            "workspace":                self.workspace,
            "started_at":               self.started_at,
            "finished_at":              self.finished_at,
            "duration_s":               self.duration_s,
            "episodes_read":            self.episodes_read,
            "episodes_compacted":       self.episodes_compacted,
            "semantic_units_created":   self.semantic_units_created,
            "semantic_units_pruned":    self.semantic_units_pruned,
            "procedures_reinforced":    self.procedures_reinforced,
            "procedures_deprecated":    self.procedures_deprecated,
            "lineage_nodes_summarized": self.lineage_nodes_summarized,
            "vectors_indexed":          self.vectors_indexed,
            "compression_ratio":        self.compression_ratio,
            "decay_applied":            self.decay_applied,
            "errors":                   self.errors,
            "metadata":                 self.metadata,
        }
