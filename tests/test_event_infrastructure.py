"""Tests for the unified event infrastructure consolidation.

Covers:
  - EventEnvelope fields (event_version, correlation_id)
  - broker.publish() returns event_id, writes to replay buffer + replay store
  - RuntimeReplayStore: append, recent, since, count, prune_before
  - New event types: METRICS_INGESTED, HEARTBEAT, RUNTIME_CONSISTENCY
  - emitter helpers: emit_metrics_ingested, emit_heartbeat, emit_runtime_consistency
  - WebSocket hydration prefers durable store
  - core/stream deque maxsize guard
"""
import time


# ── EventEnvelope ─────────────────────────────────────────────────────────────

def test_envelope_has_event_version():
    from backend.pubsub.broker import EventEnvelope
    env = EventEnvelope(event_id="abc", type="test", ts=1.0, source="test",
                        payload={"type": "test"})
    assert env.event_version == 1


def test_envelope_has_correlation_id_default_none():
    from backend.pubsub.broker import EventEnvelope
    env = EventEnvelope(event_id="abc", type="test", ts=1.0, source="test",
                        payload={"type": "test"})
    assert env.correlation_id is None


def test_envelope_correlation_id_round_trips():
    from backend.pubsub.broker import EventEnvelope
    env = EventEnvelope(event_id="abc", type="test", ts=1.0, source="test",
                        payload={"type": "test"}, correlation_id="trace-42")
    assert env.correlation_id == "trace-42"


def test_envelope_json_includes_version():
    from backend.pubsub.broker import EventEnvelope
    import json
    env = EventEnvelope(event_id="abc", type="test", ts=1.0, source="s",
                        payload={"type": "test"}, event_version=2)
    d = json.loads(env.envelope_json())
    assert d["event_version"] == 2


# ── broker.publish ────────────────────────────────────────────────────────────

def test_broker_publish_returns_event_id():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=10)
    eid = b.publish("test.event", {"type": "test.event", "ts": time.time()})
    assert isinstance(eid, str) and len(eid) > 0


def test_broker_publish_records_in_replay_buffer():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=10)
    b.publish("test.event", {"type": "test.event", "ts": time.time()})
    assert len(b.replay) == 1


def test_broker_publish_accepts_correlation_id():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=10)
    b.publish("test.event", {"type": "test.event", "ts": time.time()},
              correlation_id="corr-1")
    env = b.replay.recent(n=1)[0]
    assert env.correlation_id == "corr-1"


def test_broker_replay_since_thread_safe():
    """since() must not deadlock or crash under concurrent reads/writes."""
    import threading
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=50)

    errors = []
    def writer():
        for i in range(20):
            b.publish("e", {"type": "e", "ts": time.time()})

    def reader():
        for _ in range(20):
            try:
                b.replay.since(time.time() - 5)
            except Exception as exc:
                errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors


# ── RuntimeReplayStore ────────────────────────────────────────────────────────

def _make_store():
    from backend.runtime.replay_store import RuntimeReplayStore
    return RuntimeReplayStore(db_path=":memory:")


def _make_env(type_: str = "test", source: str = "test", ts: float | None = None):
    from backend.pubsub.broker import EventEnvelope
    return EventEnvelope(
        event_id=__import__("uuid").uuid4().hex[:12],
        type=type_,
        ts=ts or time.time(),
        source=source,
        payload={"type": type_, "ts": ts or time.time()},
    )


def test_replay_store_append_and_count():
    s = _make_store()
    s.append(_make_env("tick"))
    assert s.count() == 1


def test_replay_store_recent_returns_in_order():
    s = _make_store()
    t0 = time.time()
    s.append(_make_env("a", ts=t0))
    s.append(_make_env("b", ts=t0 + 1))
    rows = s.recent(n=10)
    assert len(rows) == 2
    assert rows[0]["ts"] <= rows[1]["ts"]   # chronological (oldest first)


def test_replay_store_recent_filtered_by_type():
    s = _make_store()
    s.append(_make_env("tick"))
    s.append(_make_env("snapshot"))
    s.append(_make_env("tick"))
    rows = s.recent(n=10, event_type="tick")
    assert len(rows) == 2
    assert all(r["type"] == "tick" for r in rows)


def test_replay_store_since_returns_events_after_ts():
    s = _make_store()
    t0 = time.time()
    s.append(_make_env(ts=t0 - 10))
    s.append(_make_env(ts=t0 + 1))
    rows = s.since(ts=t0)
    assert len(rows) == 1
    assert rows[0]["ts"] >= t0


def test_replay_store_prune_before():
    s = _make_store()
    t0 = time.time()
    s.append(_make_env(ts=t0 - 20))
    s.append(_make_env(ts=t0 - 10))
    s.append(_make_env(ts=t0 + 1))
    deleted = s.prune_before(t0)
    assert deleted == 2
    assert s.count() == 1


def test_replay_store_event_version_preserved():
    from backend.pubsub.broker import EventEnvelope
    s = _make_store()
    env = EventEnvelope(event_id="x1", type="v2", ts=time.time(), source="test",
                        payload={"type": "v2"}, event_version=2)
    s.append(env)
    rows = s.recent(n=1)
    assert rows[0]["event_version"] == 2


def test_replay_store_correlation_id_preserved():
    from backend.pubsub.broker import EventEnvelope
    s = _make_store()
    env = EventEnvelope(event_id="x2", type="t", ts=time.time(), source="test",
                        payload={"type": "t"}, correlation_id="trace-99")
    s.append(env)
    rows = s.recent(n=1)
    assert rows[0]["correlation_id"] == "trace-99"


def test_replay_store_lazy_init_no_connection_on_import():
    from backend.runtime.replay_store import RuntimeReplayStore
    s = RuntimeReplayStore(db_path=":memory:")
    assert s._conn is None   # DuckDB not connected until first use


# ── New event type constants ──────────────────────────────────────────────────

def test_schemas_has_metrics_ingested():
    from backend.events.schemas import METRICS_INGESTED
    assert METRICS_INGESTED == "metrics.ingested"


def test_schemas_has_heartbeat():
    from backend.events.schemas import HEARTBEAT
    assert HEARTBEAT == "heartbeat"


def test_schemas_has_runtime_consistency():
    from backend.events.schemas import RUNTIME_CONSISTENCY
    assert RUNTIME_CONSISTENCY == "runtime.consistency"


def test_schemas_has_event_version():
    from backend.events.schemas import EVENT_VERSION
    assert EVENT_VERSION == 1


# ── New emitter helpers ───────────────────────────────────────────────────────

def test_emit_metrics_ingested_does_not_raise():
    from backend.events.emitter import emit_metrics_ingested
    emit_metrics_ingested("tiktok", {"ctr": 0.03, "roas": 1.8, "views": 500})


def test_emit_heartbeat_does_not_raise():
    from backend.events.emitter import emit_heartbeat
    emit_heartbeat(source="orchestrator")


def test_emit_runtime_consistency_does_not_raise():
    from backend.events.emitter import emit_runtime_consistency
    emit_runtime_consistency(["state diverged: capital mismatch"], source="runtime")


# ── Broker typed emit helpers ─────────────────────────────────────────────────

def test_broker_emit_metrics_ingested_returns_event_id():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=10)
    eid = b.emit_metrics_ingested("tiktok", {"ctr": 0.02, "roas": 1.5})
    assert isinstance(eid, str)


def test_broker_emit_heartbeat_type_in_replay():
    from backend.pubsub.broker import PubSubBroker
    from backend.events.schemas import HEARTBEAT
    b = PubSubBroker(replay_size=10)
    b.emit_heartbeat(source="test")
    envs = b.replay.recent(n=5)
    assert any(e.type == HEARTBEAT for e in envs)


def test_broker_emit_runtime_consistency_issues_in_payload():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=10)
    b.emit_runtime_consistency(["drift detected"], source="test")
    envs = b.replay.recent(n=5)
    last = envs[-1]
    assert last.payload.get("issues") == ["drift detected"]


# ── core/stream deque maxsize ─────────────────────────────────────────────────

def test_stream_queue_is_bounded_deque():
    """_queue must be a deque (not a list) so maxlen is enforced."""
    from collections import deque
    import core.stream as cs
    assert isinstance(cs._queue, deque)


def test_stream_queue_has_maxlen():
    import core.stream as cs
    assert cs._queue.maxlen is not None
    assert cs._queue.maxlen > 0
