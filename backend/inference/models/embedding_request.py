"""EmbeddingRequest — input to the embedding pipeline."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmbeddingRequest:
    texts:       list[str]
    model:       str  = "default"
    normalize:   bool = True
    sequence_id: str  = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "texts":       self.texts,
            "model":       self.model,
            "normalize":   self.normalize,
            "sequence_id": self.sequence_id,
            "metadata":    self.metadata,
        }
