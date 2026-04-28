"""InferenceRequest — the canonical input to the inference router."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

RequestType = Literal["completion", "chat", "embedding", "rerank"]


@dataclass
class InferenceRequest:
    prompt: str
    model:         str            = "default"
    request_type:  RequestType    = "completion"
    max_tokens:    int            = 512
    temperature:   float          = 0.7
    system:        str | None     = None
    stream:        bool           = False
    seed:          int | None     = None
    sequence_id:   str            = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:      dict[str, Any] = field(default_factory=dict)

    # ── helpers ───────────────────────────────────────────────────────────────

    def with_seed(self, seed: int) -> "InferenceRequest":
        """Return a copy pinned to a specific seed (deterministic generation)."""
        from dataclasses import replace
        return replace(self, seed=seed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt":       self.prompt,
            "model":        self.model,
            "request_type": self.request_type,
            "max_tokens":   self.max_tokens,
            "temperature":  self.temperature,
            "system":       self.system,
            "stream":       self.stream,
            "seed":         self.seed,
            "sequence_id":  self.sequence_id,
            "metadata":     self.metadata,
        }
