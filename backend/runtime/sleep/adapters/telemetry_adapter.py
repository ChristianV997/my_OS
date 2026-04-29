"""TelemetryAdapter — live event subscription for the sleep runtime.

Subscribes to the pub/sub broker and buffers incoming events into the
EpisodicStore so the next sleep cycle can read them without querying the
replay store.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

log = logging.getLogger(__name__)

_INDEXABLE_TYPES = frozenset({
    "decision.logged",
    "campaign.launched",
    "signals.updated",
    "inference.completed",
    "vector.indexed",
})


class TelemetryAdapter:
    """Live broker subscriber that feeds events into EpisodicStore."""

    def __init__(self) -> None:
        self._sub_id: str | None = None
        self._lock   = threading.Lock()

    def _handle(self, event: dict[str, Any]) -> None:
        if event.get("type") not in _INDEXABLE_TYPES:
            return
        try:
            from backend.memory.episodic import get_episodic_store
            store = get_episodic_store()
            store.record_event(
                event_type=event.get("type", "unknown"),
                payload=event,
                source=event.get("source", ""),
                workspace=event.get("workspace", "default"),
            )
        except Exception as exc:
            log.debug("TelemetryAdapter._handle error: %s", exc)

    def start(self) -> None:
        with self._lock:
            if self._sub_id is not None:
                return
            try:
                from backend.pubsub.broker import get_broker
                self._sub_id = get_broker().subscribe(self._handle)
                log.info("sleep.TelemetryAdapter subscribed (id=%s)", self._sub_id)
            except Exception as exc:
                log.warning("sleep.TelemetryAdapter.start failed: %s", exc)

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
