"""backend.inference.models.routing_decision — schema for provider routing decisions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingDecision:
    """Records which provider/model was selected for a given request.

    Produced by the routing policy and attached to both the request telemetry
    and the InferenceResponse so the full routing path is auditable.

    Fields
    ------
    request_id      — mirrors InferenceRequest.request_id
    selected_provider — provider chosen for this request
    selected_model    — model chosen for this request
    reason          — human-readable explanation of why this provider was chosen
    fallback_order  — ordered list of providers to try if selected_provider fails
    replay_hash     — mirrors InferenceRequest.replay_hash
    sequence_id     — mirrors InferenceRequest.sequence_id
    ts              — timestamp of routing decision
    extra           — policy-specific metadata (e.g. cost estimate, latency estimate)
    """

    request_id: str = ""
    selected_provider: str = ""
    selected_model: str = ""
    reason: str = ""
    fallback_order: list[str] = field(default_factory=list)
    replay_hash: str | None = None
    sequence_id: int | None = None
    ts: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "reason": self.reason,
            "fallback_order": self.fallback_order,
            "replay_hash": self.replay_hash,
            "sequence_id": self.sequence_id,
            "ts": self.ts,
            "extra": self.extra,
        }
