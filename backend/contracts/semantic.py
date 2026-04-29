"""SemanticAsset — compressed semantic representation for cross-repo transfer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseArtifact


@dataclass
class SemanticAsset(BaseArtifact):
    """A compressed semantic unit: hook cluster, angle archetype, signal theme.

    Produced by consolidation/sleep runtime or KardashevOS_Level1 synthesis.
    Consumed by MarketOS inference and content generation.
    """
    artifact_type:     str           = field(default="semantic")
    label:             str           = field(default="")
    description:       str           = field(default="")
    embedding:         list[float]   = field(default_factory=list)
    cluster_members:   list[str]     = field(default_factory=list)
    compression_ratio: float         = field(default=0.0)
    domain:            str           = field(default="")  # hook | angle | signal | product
    score:             float         = field(default=0.0)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "label":             self.label,
            "description":       self.description,
            "embedding":         self.embedding,
            "cluster_members":   self.cluster_members,
            "compression_ratio": self.compression_ratio,
            "domain":            self.domain,
            "score":             self.score,
        })
        return d
