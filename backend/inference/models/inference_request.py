"""backend.inference.models.inference_request — canonical inference request schema."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InferenceRequest:
    """Canonical schema for a single inference request.

    Fields
    ------
    request_id      — unique identifier; auto-generated if not provided
    model           — model name/identifier (e.g. "gpt-4o", "llama3:8b")
    provider        — preferred provider hint (e.g. "openai", "ollama"); may be
                      overridden by routing policy
    prompt          — the user/system prompt text
    system_prompt   — optional system context inserted before prompt
    messages        — OpenAI-style message list; takes precedence over prompt
                      when both are provided
    temperature     — sampling temperature; None means provider default
    max_tokens      — token budget; None means provider default
    stream          — whether to request token-by-token streaming
    sequence_id     — deterministic ordering key (inherited from caller context)
    replay_hash     — deterministic content hash; auto-computed if absent
    correlation_id  — links grouped requests (e.g. multi-turn conversation)
    ts              — creation timestamp (UTC epoch float)
    extra           — provider-specific pass-through kwargs
    """

    prompt: str
    model: str = "default"
    provider: str = "auto"
    system_prompt: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    sequence_id: int | None = None
    replay_hash: str | None = None
    correlation_id: str | None = None
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.replay_hash:
            self.replay_hash = self._compute_replay_hash()

    def _compute_replay_hash(self) -> str:
        canonical = {
            "model": self.model,
            "provider": self.provider,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
            "sequence_id": self.sequence_id,
            "replay_hash": self.replay_hash,
            "correlation_id": self.correlation_id,
            "ts": self.ts,
            "extra": self.extra,
        }
