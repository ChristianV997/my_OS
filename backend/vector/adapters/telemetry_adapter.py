"""TelemetryAdapter — subscribes to the pub/sub broker and live-indexes events."""
from __future__ import annotations

import logging
import threading
from typing import Any

log = logging.getLogger(__name__)


class TelemetryAdapter:
    """Live subscriber that indexes events as they arrive on the broker.

    Call ``start()`` to begin background indexing; ``stop()`` to shut down.
    Designed for long-lived orchestrator processes.
    """

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
        self._rm   = reinforcement_memory
        self._sm   = signal_memory
        self._sub_id: str | None = None
        self._lock = threading.Lock()

    def _handle(self, event: dict[str, Any]) -> None:
        ev_type = event.get("type", "")
        try:
            if ev_type == "decision.logged":
                self._rm.record_outcome(
                    hook=event.get("hook", ""),
                    angle=event.get("angle", ""),
                    product=event.get("product", ""),
                    roas=float(event.get("roas", 0.0)),
                    phase=event.get("phase", ""),
                )
            elif ev_type == "signals.updated":
                signals = event.get("signals", [])
                if signals:
                    self._sm.index_signals(signals)
        except Exception as exc:
            log.debug("TelemetryAdapter._handle error: %s", exc)

    def start(self) -> None:
        with self._lock:
            if self._sub_id is not None:
                return
            try:
                from backend.pubsub.broker import get_broker
                broker = get_broker()
                self._sub_id = broker.subscribe(self._handle)
                log.info("TelemetryAdapter subscribed (id=%s)", self._sub_id)
            except Exception as exc:
                log.warning("TelemetryAdapter.start failed: %s", exc)

    def stop(self) -> None:
        with self._lock:
            if self._sub_id is None:
                return
            try:
                from backend.pubsub.broker import get_broker
                get_broker().unsubscribe(self._sub_id)
            except Exception:
                pass
            self._sub_id = None
            log.info("TelemetryAdapter unsubscribed")
