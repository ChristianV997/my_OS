"""backend.pubsub.broker — canonical pub/sub broker for the MarketOS event bus."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any

from backend.events.schemas import (
    LEGACY_SNAPSHOT,
    LEGACY_TICK,
    LEGACY_WORKER,
    TASK_INVENTORY,
    ORCHESTRATOR_TICK,
    RUNTIME_SNAPSHOT,
    WORKER_HEALTH,
    SIGNALS_UPDATED,
    SIMULATION_COMPLETED,
    ANOMALY_DETECTED,
    DECISION_LOGGED,
    METRICS_INGESTED,
    HEARTBEAT,
    RUNTIME_CONSISTENCY,
)

_log = logging.getLogger(__name__)


@dataclass
class EventEnvelope:
    event_id: str
    type: str
    ts: float
    source: str
    payload: dict[str, Any]
    event_version: int = 1
    correlation_id: str | None = None
    replay_hash: str | None = None

    def payload_json(self) -> str:
        return json.dumps(self.payload, default=str)

    def envelope_json(self) -> str:
        return json.dumps({
            "event_id": self.event_id,
            "type": self.type,
            "ts": self.ts,
            "source": self.source,
            "event_version": self.event_version,
            "correlation_id": self.correlation_id,
            "replay_hash": self.replay_hash,
            **self.payload,
        }, default=str)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def deterministic_replay_hash(
    event_type: str,
    payload: dict[str, Any],
) -> str:
    canonical = {
        "event_type": event_type,
        "payload": payload,
    }

    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()


class ReplayBuffer:

    def __init__(self, max_size: int = 100):
        self._buf: deque[EventEnvelope] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def record(self, env: EventEnvelope) -> None:
        with self._lock:
            self._buf.append(env)

    def recent(self, n: int = 50) -> list[EventEnvelope]:
        with self._lock:
            buf = sorted(
                list(self._buf),
                key=lambda e: (
                    e.ts,
                    e.replay_hash or "",
                ),
            )

        return buf[-n:] if len(buf) > n else buf

    def since(self, ts: float) -> list[EventEnvelope]:
        with self._lock:
            return [e for e in self._buf if e.ts >= ts]


class PubSubBroker:

    def __init__(self, replay_size: int = 200):
        self.replay = ReplayBuffer(max_size=replay_size)

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        source: str = "system",
        correlation_id: str | None = None,
    ) -> str:

        replay_hash = deterministic_replay_hash(
            event_type,
            payload,
        )

        env = EventEnvelope(
            event_id=_new_id(),
            type=event_type,
            ts=payload.get("ts", time.time()),
            source=source,
            payload=payload,
            correlation_id=correlation_id,
            replay_hash=replay_hash,
        )

        try:
            from core.stream import publish as _stream_publish
            _stream_publish(payload)
        except Exception as exc:
            _log.warning(
                "broker_stream_publish_failed type=%s error=%s",
                event_type,
                exc,
            )

        self.replay.record(env)

        try:
            from backend.runtime.replay_store import runtime_replay_store
            runtime_replay_store.append(env)
        except Exception as exc:
            _log.warning(
                "broker_replay_store_append_failed type=%s error=%s",
                event_type,
                exc,
            )

        return env.event_id


broker = PubSubBroker(replay_size=200)
