"""SemanticCheckpoint — snapshot of SemanticStore at a consolidation point."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticCheckpoint:
    """Immutable snapshot of the SemanticStore taken after a consolidation pass.

    Used to:
    - bootstrap the next sleep cycle without re-reading all episodes
    - detect drift between generations
    - provide a deterministic restore point
    - emit as a replayable event
    """
    checkpoint_id: str
    generation:    int
    workspace:     str              = "default"
    created_at:    float            = field(default_factory=time.time)
    domains:       dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    unit_count:    int              = 0
    cycle_id:      str              = ""
    parent_checkpoint_id: str       = ""

    @classmethod
    def from_semantic_store(
        cls,
        checkpoint_id: str,
        cycle_id: str,
        workspace: str = "default",
        parent_checkpoint_id: str = "",
    ) -> "SemanticCheckpoint":
        from backend.memory.semantic import get_semantic_store
        store = get_semantic_store()
        snap  = store.snapshot()
        unit_count = sum(len(units) for units in snap.get("domains", {}).values())
        return cls(
            checkpoint_id=checkpoint_id,
            generation=snap.get("generation", 0),
            workspace=workspace,
            domains=snap.get("domains", {}),
            unit_count=unit_count,
            cycle_id=cycle_id,
            parent_checkpoint_id=parent_checkpoint_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id":        self.checkpoint_id,
            "generation":           self.generation,
            "workspace":            self.workspace,
            "created_at":           self.created_at,
            "unit_count":           self.unit_count,
            "cycle_id":             self.cycle_id,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            # Omit full domain data from event payload — too large
            "domain_names":         list(self.domains.keys()),
        }
