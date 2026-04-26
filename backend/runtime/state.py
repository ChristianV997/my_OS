"""backend.runtime.state — canonical serialisable snapshot of the full runtime.

Every component that needs to push state over WebSocket or store a point-in-time
snapshot should call ``build_snapshot(state)`` and serialise the result.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuntimeSnapshot:
    ts: float = field(default_factory=time.time)
    type: str = "snapshot"
    # lifecycle
    cycle: int = 0
    phase: str = "RESEARCH"
    # capital & performance
    capital: float = 0.0
    avg_roas: float = 0.0
    win_rate: float = 0.0
    regime: str = "unknown"
    signal_count: int = 0
    # top signals (list of {product, score, source, ...})
    top_signals: list[dict[str, Any]] = field(default_factory=list)
    # top playbooks (list of Playbook.to_dict())
    top_playbooks: list[dict[str, Any]] = field(default_factory=list)
    # content patterns from PatternStore
    patterns: dict[str, Any] = field(default_factory=dict)
    # recent decisions for decision log panel
    recent_decisions: list[dict[str, Any]] = field(default_factory=list)
    # worker health from last orchestrator tick
    worker_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


def build_snapshot(state: Any, phase: str = "RESEARCH") -> RuntimeSnapshot:
    """Build a RuntimeSnapshot from a live SystemState + auxiliary singletons."""
    rows = state.event_log.rows[-20:] if state.event_log.rows else []
    avg_roas = sum(r.get("roas", 0.0) for r in rows) / max(len(rows), 1)
    winners  = sum(1 for r in rows if r.get("roas", 0.0) >= 1.5)
    win_rate = winners / max(len(rows), 1)

    # Phase + signal count from phase controller
    signal_count = 0
    try:
        from core.system.phase_controller import phase_controller
        signal_count = phase_controller.status().get("signal_count", 0)
        phase = phase_controller.current.value
    except Exception:
        pass

    # Top signals
    top_signals: list[dict] = []
    try:
        from core.signals import signal_engine
        sigs = signal_engine.get()
        top_signals = signal_engine.top_opportunities(sigs, n=5)
    except Exception:
        pass

    # Top playbooks
    top_playbooks: list[dict] = []
    try:
        from core.content.playbook import playbook_memory
        top_playbooks = [vars(p) for p in playbook_memory.all()[:5]]
    except Exception:
        pass

    # Content patterns
    patterns: dict = {}
    try:
        from core.content.patterns import pattern_store
        patterns = pattern_store.get_patterns()
    except Exception:
        pass

    # Recent decisions
    recent_decisions = rows[-10:]

    return RuntimeSnapshot(
        cycle=state.total_cycles,
        phase=phase,
        capital=round(state.capital, 2),
        avg_roas=round(avg_roas, 4),
        win_rate=round(win_rate, 4),
        regime=state.detected_regime or "unknown",
        signal_count=signal_count,
        top_signals=top_signals,
        top_playbooks=top_playbooks,
        patterns=patterns,
        recent_decisions=recent_decisions,
    )
