"""InferenceResponse — the canonical output from the inference router."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InferenceResponse:
    content:           str
    provider:          str
    model:             str
    sequence_id:       str
    replay_hash:       str
    latency_ms:        float

    # token accounting
    prompt_tokens:     int   = 0
    completion_tokens: int   = 0

    # fallback metadata
    fallback_used:     bool       = False
    fallback_reason:   str | None = None

    # cache / replay flags
    cached:            bool       = False
    replayed:          bool       = False

    # error surface (non-fatal failures set content="" and error=<msg>)
    error:             str | None = None

    timestamp:         float      = field(default_factory=time.time)

    # ── helpers ───────────────────────────────────────────────────────────────

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content":           self.content,
            "provider":          self.provider,
            "model":             self.model,
            "sequence_id":       self.sequence_id,
            "replay_hash":       self.replay_hash,
            "latency_ms":        round(self.latency_ms, 3),
            "prompt_tokens":     self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens":      self.total_tokens,
            "fallback_used":     self.fallback_used,
            "fallback_reason":   self.fallback_reason,
            "cached":            self.cached,
            "replayed":          self.replayed,
            "error":             self.error,
            "timestamp":         self.timestamp,
        }
