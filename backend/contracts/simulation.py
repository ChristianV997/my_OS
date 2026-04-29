"""SimulationArtifact — output of ScienceR-Dsim topology simulations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseArtifact


@dataclass
class SimulationArtifact(BaseArtifact):
    """Validated output of a simulation run.

    Carries: trajectory data, topology parameters, extracted defects,
    and the replay hash linking back to the simulation inputs.
    """
    artifact_type:     str             = field(default="simulation")
    simulation_id:     str             = field(default="")
    regime:            str             = field(default="")       # e.g. EXPLORE / SCALE
    trajectory:        list[dict]      = field(default_factory=list)
    topology_params:   dict[str, Any]  = field(default_factory=dict)
    defects:           list[dict]      = field(default_factory=list)
    scores:            list[dict]      = field(default_factory=list)
    top_product:       str             = field(default="")
    signals_scored:    int             = field(default=0)
    source_repo:       str             = field(default="ScienceR-Dsim")

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "simulation_id":   self.simulation_id,
            "regime":          self.regime,
            "trajectory":      self.trajectory,
            "topology_params": self.topology_params,
            "defects":         self.defects,
            "scores":          self.scores,
            "top_product":     self.top_product,
            "signals_scored":  self.signals_scored,
            "source_repo":     self.source_repo,
        })
        return d
