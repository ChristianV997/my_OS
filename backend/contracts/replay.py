"""ReplayArtifact — a replayable execution snapshot for deterministic recovery."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseArtifact


@dataclass
class ReplayArtifact(BaseArtifact):
    """Captures enough state to replay a deterministic execution from scratch.

    Written by the orchestrator at the start of each phase cycle.
    The replay runtime reads this to reconstruct exact preconditions.
    """
    artifact_type:  str             = field(default="replay")
    sequence_id:    str             = field(default="")
    event_count:    int             = field(default=0)
    state_hash:     str             = field(default="")
    phase:          str             = field(default="")
    capital:        float           = field(default=0.0)
    avg_roas:       float           = field(default=0.0)
    active_campaigns: list[str]     = field(default_factory=list)
    pattern_snapshot: dict[str, Any] = field(default_factory=dict)
    config_snapshot:  dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "sequence_id":      self.sequence_id,
            "event_count":      self.event_count,
            "state_hash":       self.state_hash,
            "phase":            self.phase,
            "capital":          self.capital,
            "avg_roas":         self.avg_roas,
            "active_campaigns": self.active_campaigns,
            "pattern_snapshot": self.pattern_snapshot,
            "config_snapshot":  self.config_snapshot,
        })
        return d
