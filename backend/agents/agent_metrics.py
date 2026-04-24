"""Agent Metrics & Logging — PnL tracking, decision counting, and drift detection.

Each agent that registers with ``AgentMetricsRegistry`` gets a dedicated
``AgentMetrics`` slot that tracks:

* cumulative PnL (revenue − cost)
* decision counts per action type
* rolling mean prediction error (for drift detection)
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Per-agent metrics container
# ---------------------------------------------------------------------------


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    agent_name: str
    total_decisions: int = 0
    decisions_by_action: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cumulative_pnl: float = 0.0
    _error_window: deque = field(default_factory=lambda: deque(maxlen=100), repr=False)

    def record_decision(self, action: str) -> None:
        self.total_decisions += 1
        self.decisions_by_action[action] += 1

    def record_pnl(self, revenue: float, cost: float) -> None:
        self.cumulative_pnl += revenue - cost

    def record_prediction_error(self, predicted: float, actual: float) -> None:
        self._error_window.append(predicted - actual)

    def mean_prediction_error(self) -> float:
        if not self._error_window:
            return 0.0
        return sum(self._error_window) / len(self._error_window)

    def drift_detected(self, threshold: float = 0.5) -> bool:
        """Simple drift flag: mean absolute error > *threshold*."""
        if len(self._error_window) < 10:
            return False
        mae = sum(abs(e) for e in self._error_window) / len(self._error_window)
        return mae > threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent_name,
            "total_decisions": self.total_decisions,
            "decisions_by_action": dict(self.decisions_by_action),
            "cumulative_pnl": round(self.cumulative_pnl, 4),
            "mean_prediction_error": round(self.mean_prediction_error(), 6),
            "drift_detected": self.drift_detected(),
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class AgentMetricsRegistry:
    """Thread-safe registry for agent metrics.

    Usage::

        registry = AgentMetricsRegistry()
        registry.record_decision("scaling", "scale")
        registry.record_pnl("scaling", revenue=300.0, cost=100.0)
        registry.snapshot()   # → list of per-agent dicts
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._agents: dict[str, AgentMetrics] = {}

    def _get_or_create(self, agent_name: str) -> AgentMetrics:
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentMetrics(agent_name=agent_name)
        return self._agents[agent_name]

    def record_decision(self, agent_name: str, action: str) -> None:
        with self._lock:
            self._get_or_create(agent_name).record_decision(action)

    def record_pnl(self, agent_name: str, revenue: float, cost: float) -> None:
        with self._lock:
            self._get_or_create(agent_name).record_pnl(revenue, cost)

    def record_prediction_error(
        self, agent_name: str, predicted: float, actual: float
    ) -> None:
        with self._lock:
            self._get_or_create(agent_name).record_prediction_error(predicted, actual)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [m.to_dict() for m in self._agents.values()]

    def get(self, agent_name: str) -> dict[str, Any] | None:
        with self._lock:
            m = self._agents.get(agent_name)
            return m.to_dict() if m else None

    def agent_names(self) -> list[str]:
        with self._lock:
            return list(self._agents.keys())


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

agent_metrics_registry = AgentMetricsRegistry()
