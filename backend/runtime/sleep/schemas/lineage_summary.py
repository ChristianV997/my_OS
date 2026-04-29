"""LineageSummary — compressed summary of a lineage subtree."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineageSummary:
    """A summary node representing a collapsed lineage subtree.

    When a lineage branch grows too deep, the summarization pass replaces
    the interior nodes with a single LineageSummary that preserves:
    - the root and tip node IDs (for traceability)
    - the count and types of collapsed nodes
    - the replay_hash chain (for deterministic re-expansion)
    - the workspace boundary (for isolation)
    """
    summary_id:      str
    workspace:       str            = "default"
    root_node_id:    str            = ""
    tip_node_id:     str            = ""
    collapsed_count: int            = 0
    node_types:      list[str]      = field(default_factory=list)
    replay_hashes:   list[str]      = field(default_factory=list)
    cycle_id:        str            = ""
    created_at:      float          = 0.0
    metadata:        dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id":      self.summary_id,
            "workspace":       self.workspace,
            "root_node_id":    self.root_node_id,
            "tip_node_id":     self.tip_node_id,
            "collapsed_count": self.collapsed_count,
            "node_types":      self.node_types,
            "replay_hashes":   self.replay_hashes,
            "cycle_id":        self.cycle_id,
            "created_at":      self.created_at,
            "metadata":        self.metadata,
        }
