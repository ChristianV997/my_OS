"""RoutingDecision — captures which provider was selected and why."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingDecision:
    sequence_id:       str
    selected_provider: str
    selected_model:    str
    reason:            str
    fallback_chain:    list[str]
    timestamp:         float = field(default_factory=time.time)
    cost_estimate_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id":       self.sequence_id,
            "selected_provider": self.selected_provider,
            "selected_model":    self.selected_model,
            "reason":            self.reason,
            "fallback_chain":    self.fallback_chain,
            "timestamp":         self.timestamp,
            "cost_estimate_usd": self.cost_estimate_usd,
        }
