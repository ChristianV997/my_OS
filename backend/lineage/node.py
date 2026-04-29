"""LineageNode — atomic unit of the causal graph."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineageNode:
    """One node in the causal lineage graph.

    A node represents any artifact, event, or computation that produced
    or consumed data.  Edges are expressed as ``parent_ids`` (backward
    pointers) so the full ancestry can be reconstructed without storing
    edges separately.
    """
    node_id:     str                     # deterministic ID (UUID5 or artifact_id)
    node_type:   str                     # artifact type or event type
    label:       str              = ""   # human-readable name
    ts:          float            = field(default_factory=time.time)
    parent_ids:  list[str]        = field(default_factory=list)
    workspace:   str              = "default"
    source:      str              = ""   # originating system/module
    payload:     dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":    self.node_id,
            "node_type":  self.node_type,
            "label":      self.label,
            "ts":         self.ts,
            "parent_ids": self.parent_ids,
            "workspace":  self.workspace,
            "source":     self.source,
            "payload":    self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LineageNode":
        return cls(
            node_id=d["node_id"],
            node_type=d.get("node_type", ""),
            label=d.get("label", ""),
            ts=d.get("ts", time.time()),
            parent_ids=d.get("parent_ids", []),
            workspace=d.get("workspace", "default"),
            source=d.get("source", ""),
            payload=d.get("payload", {}),
        )
