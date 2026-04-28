"""backend.inference.models.inference_response — canonical inference response schema."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class InferenceResponse:
    """Canonical schema for a completed inference response.

    Fields
    ------
    request_id      — mirrors the originating InferenceRequest.request_id
    model           — actual model that served the response
    provider        — actual provider that served the response
    text            — generated text (full for non-streaming; final for streaming)
    usage           — token usage counts
    latency_ms      — wall-clock time from request dispatch to response receipt
    sequence_id     — deterministic ordering key (mirrors request)
    replay_hash     — deterministic hash (mirrors request)
    correlation_id  — mirrors request correlation_id
    fallback_used   — True if this response came from a fallback provider
    fallback_chain  — ordered list of providers tried before success
    stream          — whether the response was streamed
    ts              — response timestamp (UTC epoch float)
    error           — None on success; error string on failure
    extra           — provider-specific metadata
    """

    request_id: str = ""
    model: str = ""
    provider: str = ""
    text: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    sequence_id: int | None = None
    replay_hash: str | None = None
    correlation_id: str | None = None
    fallback_used: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    stream: bool = False
    ts: float = field(default_factory=time.time)
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "text": self.text,
            "usage": self.usage.to_dict(),
            "latency_ms": self.latency_ms,
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "correlation_id": self.correlation_id,
            "fallback_used": self.fallback_used,
            "fallback_chain": self.fallback_chain,
            "stream": self.stream,
            "ts": self.ts,
            "error": self.error,
            "extra": self.extra,
        }
