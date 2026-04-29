"""Worldline — ordered trajectory of a single computational thread.

Inspired by spacetime worldlines: a Worldline is the complete ordered
sequence of states that a computation (signal, campaign, simulation) passes
through from origin to terminus.

Each step in the Worldline is a LineageNode.  The Worldline tracks
causal ordering, branching (forks), and merging (joins).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .node import LineageNode


@dataclass
class Worldline:
    """An ordered causal trajectory.

    ``worldline_id`` identifies this computational thread.
    ``steps`` is the ordered list of LineageNodes in traversal order.
    """
    worldline_id: str
    label:        str              = ""
    workspace:    str              = "default"
    steps:        list[LineageNode] = field(default_factory=list)
    forked_from:  str              = ""   # parent worldline_id if this is a branch
    merged_into:  str              = ""   # downstream worldline_id if joined
    created_at:   float            = field(default_factory=time.time)
    terminated_at: float           = 0.0
    metadata:     dict[str, Any]   = field(default_factory=dict)

    def append_step(self, node: LineageNode) -> None:
        self.steps.append(node)

    def terminate(self) -> None:
        self.terminated_at = time.time()

    def duration_s(self) -> float:
        if self.terminated_at > 0:
            return self.terminated_at - self.created_at
        return time.time() - self.created_at

    def root_id(self) -> str | None:
        return self.steps[0].node_id if self.steps else None

    def tip_id(self) -> str | None:
        return self.steps[-1].node_id if self.steps else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "worldline_id":  self.worldline_id,
            "label":         self.label,
            "workspace":     self.workspace,
            "step_ids":      [s.node_id for s in self.steps],
            "forked_from":   self.forked_from,
            "merged_into":   self.merged_into,
            "created_at":    self.created_at,
            "terminated_at": self.terminated_at,
            "duration_s":    self.duration_s(),
            "metadata":      self.metadata,
        }
