"""ResearchArtifact — output of KardashevOS_Level1 synthesis operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import BaseArtifact


@dataclass
class ResearchArtifact(BaseArtifact):
    """Distilled research or semantic synthesis output.

    Produced by KardashevOS_Level1 council operations, long-form reasoning,
    or scientific abstraction pipelines.
    """
    artifact_type:   str            = field(default="research")
    title:           str            = field(default="")
    abstract:        str            = field(default="")
    body:            str            = field(default="")
    keywords:        list[str]      = field(default_factory=list)
    citations:       list[str]      = field(default_factory=list)
    compression_ratio: float        = field(default=0.0)
    source_repo:     str            = field(default="KardashevOS_Level1")
    format:          str            = field(default="text")  # text | paper | book | report

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "title":             self.title,
            "abstract":          self.abstract,
            "body":              self.body,
            "keywords":          self.keywords,
            "citations":         self.citations,
            "compression_ratio": self.compression_ratio,
            "source_repo":       self.source_repo,
            "format":            self.format,
        })
        return d
