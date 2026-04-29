"""WorkflowArtifact — typed output of a deterministic MarketOS execution workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseArtifact


@dataclass
class WorkflowArtifact(BaseArtifact):
    """Captures the inputs, outputs, and execution trace of one workflow run.

    Used by the orchestrator for each phase cycle so the full execution
    can be replayed or audited from the lineage graph.
    """
    artifact_type:  str             = field(default="workflow")
    workflow_name:  str             = field(default="")
    phase:          str             = field(default="")
    inputs:         dict[str, Any]  = field(default_factory=dict)
    outputs:        dict[str, Any]  = field(default_factory=dict)
    steps:          list[dict]      = field(default_factory=list)
    duration_s:     float           = field(default=0.0)
    success:        bool            = field(default=True)
    error:          str             = field(default="")

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "workflow_name": self.workflow_name,
            "phase":         self.phase,
            "inputs":        self.inputs,
            "outputs":       self.outputs,
            "steps":         self.steps,
            "duration_s":    self.duration_s,
            "success":       self.success,
            "error":         self.error,
        })
        return d
