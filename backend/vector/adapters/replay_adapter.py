"""ReplayAdapter — reads the runtime replay store and rehydrates vector memory."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class ReplayAdapter:
    """Pulls events from RuntimeReplayStore and indexes relevant payloads."""

    def __init__(
        self,
        reinforcement_memory=None,
        signal_memory=None,
    ) -> None:
        if reinforcement_memory is None:
            from ..memory.reinforcement_memory import ReinforcementMemory
            reinforcement_memory = ReinforcementMemory()
        if signal_memory is None:
            from ..memory.signal_memory import SignalMemory
            signal_memory = SignalMemory()
        self._rm = reinforcement_memory
        self._sm = signal_memory

    def rehydrate_from_replay(self, limit: int = 500) -> dict[str, int]:
        """Read last *limit* events from replay store and index them."""
        counts: dict[str, int] = {"outcomes": 0, "signals": 0}
        try:
            from backend.runtime.replay_store import get_replay_store
            store  = get_replay_store()
            events = store.tail(limit)
        except Exception as exc:
            log.warning("ReplayAdapter.rehydrate failed: %s", exc)
            return counts

        for ev in events:
            ev_type = ev.get("type", "")
            if ev_type == "decision.logged":
                try:
                    self._rm.record_outcome(
                        hook=ev.get("hook", ""),
                        angle=ev.get("angle", ""),
                        product=ev.get("product", ""),
                        roas=float(ev.get("roas", 0.0)),
                        phase=ev.get("phase", ""),
                        sequence_id=ev.get("sequence_id", ""),
                    )
                    counts["outcomes"] += 1
                except Exception:
                    pass
            elif ev_type in ("signals.updated", "signal.ingested"):
                signals = ev.get("signals", [])
                if signals:
                    try:
                        self._sm.index_signals(signals)
                        counts["signals"] += len(signals)
                    except Exception:
                        pass
        return counts
