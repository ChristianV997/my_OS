"""backend.pubsub.broker — canonical pub/sub broker for the MarketOS event bus.

Architecture
------------
All publishers call ``broker.publish(type, payload, source)`` or the typed
convenience helpers (``emit_snapshot``, ``emit_tick``, etc.).

Internally the broker:
  1. Wraps the payload in an EventEnvelope (adds event_id, source, ts).
  2. Calls ``core.stream.publish(payload)`` to push to Redis/in-memory queue.
     The payload dict is the original event dict — NOT the envelope — so the
     existing WebSocket wire format stays unchanged and the frontend needs no
     updates.
  3. Records the envelope in an in-memory ReplayBuffer so reconnecting
     WebSocket clients can be hydrated with the last N events.

All consumers call ``broker.consume()`` which returns typed EventEnvelopes.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator

from backend.events.schemas import (
    LEGACY_SNAPSHOT, LEGACY_TICK, LEGACY_WORKER, TASK_INVENTORY,
    ORCHESTRATOR_TICK, RUNTIME_SNAPSHOT, WORKER_HEALTH,
    SIGNALS_UPDATED, SIMULATION_COMPLETED, ANOMALY_DETECTED, DECISION_LOGGED,
    METRICS_INGESTED, HEARTBEAT, RUNTIME_CONSISTENCY,
)

_log = logging.getLogger(__name__)


# ── Event envelope ────────────────────────────────────────────────────────────

@dataclass
class EventEnvelope:
    """Typed wrapper around a raw event dict.

    ``payload`` is always the legacy event dict (has a ``type`` key) so it
    can be transmitted to existing WebSocket clients unchanged.

    Fields
    ------
    event_id       — 12-char UUID hex, unique per event
    type           — canonical dotted type string (e.g. "orchestrator.tick")
    ts             — Unix timestamp (float)
    source         — publisher identifier (orchestrator, api, simulation, …)
    payload        — original event dict (preserved for wire compat)
    event_version  — schema version (increment on breaking payload changes)
    correlation_id — optional trace ID for linking related events
    """
    event_id:       str
    type:           str
    ts:             float
    source:         str
    payload:        dict[str, Any]
    event_version:  int            = 1
    correlation_id: str | None     = None

    def payload_json(self) -> str:
        """Return the payload as a JSON string (existing wire format)."""
        return json.dumps(self.payload, default=str)

    def envelope_json(self) -> str:
        """Return the full envelope as a JSON string (for debugging/logging)."""
        return json.dumps({
            "event_id":       self.event_id,
            "type":           self.type,
            "ts":             self.ts,
            "source":         self.source,
            "event_version":  self.event_version,
            "correlation_id": self.correlation_id,
            **self.payload,
        }, default=str)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Replay buffer ─────────────────────────────────────────────────────────────

class ReplayBuffer:
    """Thread-safe circular buffer of recent EventEnvelopes.

    Used to hydrate reconnecting WebSocket clients with the last N events
    so they don't start with a blank state.
    """

    def __init__(self, max_size: int = 100):
        self._buf: deque[EventEnvelope] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def record(self, env: EventEnvelope) -> None:
        with self._lock:
            self._buf.append(env)

    def recent(self, n: int = 50) -> list[EventEnvelope]:
        with self._lock:
            buf = list(self._buf)
        return buf[-n:] if len(buf) > n else buf

    def since(self, ts: float) -> list[EventEnvelope]:
        with self._lock:
            return [e for e in self._buf if e.ts >= ts]

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)


# ── Broker ────────────────────────────────────────────────────────────────────

class PubSubBroker:
    """Single pub/sub entry point for the entire runtime.

    Thread-safe: all public methods are safe to call from background threads,
    async handlers, and Celery workers concurrently.
    """

    def __init__(self, replay_size: int = 200):
        self.replay = ReplayBuffer(max_size=replay_size)

    # ------------------------------------------------------------------
    # Core publish / consume
    # ------------------------------------------------------------------

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "system",
        correlation_id: str | None = None,
    ) -> str:
        """Publish one event.  Returns the event_id.

        The ``payload`` dict must already contain a ``"type"`` key equal to
        ``event_type`` so legacy consumers keep working.
        """
        env = EventEnvelope(
            event_id=_new_id(),
            type=event_type,
            ts=payload.get("ts", time.time()),
            source=source,
            payload=payload,
            correlation_id=correlation_id,
        )
        # push to Redis / in-memory stream (existing path — never change)
        try:
            from core.stream import publish as _stream_publish
            _stream_publish(payload)
        except Exception as exc:
            _log.warning("broker_stream_publish_failed type=%s error=%s", event_type, exc)

        # record in in-process replay buffer (fast, lost on restart)
        self.replay.record(env)

        # persist to durable replay store (survives restart, supports backtesting)
        try:
            from backend.runtime.replay_store import runtime_replay_store
            runtime_replay_store.append(env)
        except Exception as exc:
            _log.warning("broker_replay_store_append_failed type=%s error=%s", event_type, exc)

        return env.event_id

    def consume(self, group: str = "ws", consumer: str = "c1") -> list[EventEnvelope]:
        """Consume pending events from the stream.  Returns typed envelopes."""
        try:
            from core.stream import consume as _stream_consume
            raw = _stream_consume(group=group, consumer=consumer)
        except Exception as exc:
            _log.warning("broker_consume_failed error=%s", exc)
            return []

        envelopes: list[EventEnvelope] = []
        for _, messages in (raw or []):
            for _, msg in messages:
                try:
                    payload = json.loads(msg.get("data", "{}"))
                    envelopes.append(EventEnvelope(
                        event_id=msg.get("event_id", _new_id()),
                        type=payload.get("type", "unknown"),
                        ts=float(payload.get("ts", time.time())),
                        source=payload.get("_source", "system"),
                        payload=payload,
                    ))
                except Exception:
                    pass
        return envelopes

    # ------------------------------------------------------------------
    # Typed emit helpers
    # ------------------------------------------------------------------

    def emit_snapshot(self, snap: Any) -> str:
        """Emit a RuntimeSnapshot.  ``snap`` may be a dataclass or dict."""
        if hasattr(snap, "to_dict"):
            payload = snap.to_dict()
        else:
            payload = dict(snap)
        payload.setdefault("type", LEGACY_SNAPSHOT)
        payload.setdefault("ts", time.time())
        return self.publish(LEGACY_SNAPSHOT, payload, source="api")

    def emit_tick(
        self,
        phase: str,
        avg_roas: float,
        capital: float,
        win_rate: float = 0.0,
        signal_count: int = 0,
        source: str = "orchestrator",
    ) -> str:
        payload = {
            "type":         LEGACY_TICK,
            "phase":        phase,
            "avg_roas":     avg_roas,
            "capital":      capital,
            "win_rate":     win_rate,
            "signal_count": signal_count,
            "ts":           time.time(),
        }
        return self.publish(ORCHESTRATOR_TICK, payload, source=source)

    def emit_worker_health(
        self,
        worker: str,
        status: str,
        phase: str = "",
        source: str = "orchestrator",
        **extra: Any,
    ) -> str:
        payload = {
            "type":   LEGACY_WORKER,
            "worker": worker,
            "status": status,
            "phase":  phase,
            "ts":     time.time(),
        }
        payload.update({k: v for k, v in extra.items()
                        if isinstance(v, (int, float, str, bool))})
        return self.publish(WORKER_HEALTH, payload, source=source)

    def emit_task_inventory(self, inv: dict) -> str:
        inv.setdefault("type", TASK_INVENTORY)
        inv.setdefault("ts", time.time())
        return self.publish(TASK_INVENTORY, inv, source="task_registry")

    def emit_signals_updated(self, signals: list[dict], source: str = "api") -> str:
        payload = {
            "type":    SIGNALS_UPDATED,
            "signals": signals,
            "count":   len(signals),
            "ts":      time.time(),
        }
        return self.publish(SIGNALS_UPDATED, payload, source=source)

    def emit_simulation_completed(
        self,
        scores: list[dict],
        top_product: str | None = None,
        source: str = "simulation",
    ) -> str:
        payload = {
            "type":          SIMULATION_COMPLETED,
            "scores":        scores,
            "top_product":   top_product,
            "signals_scored": len(scores),
            "ts":            time.time(),
        }
        return self.publish(SIMULATION_COMPLETED, payload, source=source)

    def emit_anomaly(
        self,
        level: str,
        message: str,
        source: str = "system",
    ) -> str:
        payload = {
            "type":    ANOMALY_DETECTED,
            "level":   level,
            "message": message,
            "source":  source,
            "ts":      time.time(),
        }
        return self.publish(ANOMALY_DETECTED, payload, source=source)

    def emit_decision(
        self,
        product: str,
        roas: float,
        label: str,
        hook: str = "",
        angle: str = "",
        source: str = "api",
        **extra: Any,
    ) -> str:
        payload = {
            "type":    DECISION_LOGGED,
            "product": product,
            "roas":    roas,
            "label":   label,
            "hook":    hook,
            "angle":   angle,
            "ts":      time.time(),
        }
        payload.update({k: v for k, v in extra.items()
                        if isinstance(v, (int, float, str, bool))})
        return self.publish(DECISION_LOGGED, payload, source=source)

    def emit_metrics_ingested(
        self,
        source: str,
        metrics: dict[str, Any],
    ) -> str:
        payload = {
            "type":    METRICS_INGESTED,
            "source":  source,
            "metrics": {k: v for k, v in metrics.items()
                        if isinstance(v, (int, float, str, bool))},
            "ts":      time.time(),
        }
        return self.publish(METRICS_INGESTED, payload, source=source)

    def emit_heartbeat(self, source: str = "system") -> str:
        payload = {
            "type":   HEARTBEAT,
            "source": source,
            "ts":     time.time(),
        }
        return self.publish(HEARTBEAT, payload, source=source)

    def emit_runtime_consistency(
        self,
        issues: list[str],
        source: str = "runtime",
    ) -> str:
        payload = {
            "type":   RUNTIME_CONSISTENCY,
            "issues": issues,
            "source": source,
            "ts":     time.time(),
        }
        return self.publish(RUNTIME_CONSISTENCY, payload, source=source)


# ── module-level singleton ─────────────────────────────────────────────────────

broker = PubSubBroker(replay_size=200)
