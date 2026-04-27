"""Tests for the backend.pubsub canonical pub/sub broker."""
import json
import time


# ── EventEnvelope ─────────────────────────────────────────────────────────────

def test_event_envelope_payload_json():
    from backend.pubsub.broker import EventEnvelope
    env = EventEnvelope(
        event_id="abc123",
        type="snapshot",
        ts=1234567890.0,
        source="api",
        payload={"type": "snapshot", "ts": 1234567890.0, "cycle": 5},
    )
    j = env.payload_json()
    d = json.loads(j)
    assert d["cycle"] == 5
    assert d["type"] == "snapshot"


def test_event_envelope_envelope_json_has_event_id():
    from backend.pubsub.broker import EventEnvelope
    env = EventEnvelope(
        event_id="xyz789",
        type="tick",
        ts=time.time(),
        source="orchestrator",
        payload={"type": "tick", "phase": "RESEARCH"},
    )
    j = env.envelope_json()
    d = json.loads(j)
    assert d["event_id"] == "xyz789"
    assert d["source"] == "orchestrator"


# ── ReplayBuffer ──────────────────────────────────────────────────────────────

def test_replay_buffer_records_and_returns_recent():
    from backend.pubsub.broker import EventEnvelope, ReplayBuffer
    buf = ReplayBuffer(max_size=10)
    for i in range(5):
        buf.record(EventEnvelope(
            event_id=str(i), type="tick", ts=float(i),
            source="test", payload={"type": "tick", "i": i},
        ))
    recent = buf.recent(n=3)
    assert len(recent) == 3
    assert recent[-1].payload["i"] == 4


def test_replay_buffer_respects_max_size():
    from backend.pubsub.broker import EventEnvelope, ReplayBuffer
    buf = ReplayBuffer(max_size=3)
    for i in range(10):
        buf.record(EventEnvelope(
            event_id=str(i), type="t", ts=float(i),
            source="s", payload={"type": "t", "i": i},
        ))
    assert len(buf) == 3
    assert buf.recent()[-1].payload["i"] == 9


def test_replay_buffer_since_filters_by_ts():
    from backend.pubsub.broker import EventEnvelope, ReplayBuffer
    buf = ReplayBuffer(max_size=20)
    now = time.time()
    for i in range(5):
        buf.record(EventEnvelope(
            event_id=str(i), type="t", ts=now + i,
            source="s", payload={"type": "t"},
        ))
    since = buf.since(now + 2)
    assert len(since) == 3   # ts=now+2, now+3, now+4


# ── PubSubBroker ──────────────────────────────────────────────────────────────

def test_broker_publish_adds_to_replay():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker(replay_size=50)
    before = len(b.replay)
    b.publish("tick", {"type": "tick", "phase": "RESEARCH", "ts": time.time()}, source="test")
    assert len(b.replay) == before + 1


def test_broker_publish_returns_event_id():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker()
    eid = b.publish("tick", {"type": "tick", "ts": time.time()})
    assert isinstance(eid, str)
    assert len(eid) > 0


def test_broker_emit_tick_payload_shape():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker()
    b.emit_tick("EXPLORE", avg_roas=1.4, capital=820.0, win_rate=0.6, signal_count=12)
    env = b.replay.recent(n=1)[0]
    assert env.payload["phase"] == "EXPLORE"
    assert env.payload["avg_roas"] == 1.4
    assert env.payload["capital"] == 820.0
    assert env.payload["type"] == "tick"


def test_broker_emit_snapshot_sets_type():
    from backend.pubsub.broker import PubSubBroker
    from backend.runtime.state import RuntimeSnapshot
    b = PubSubBroker()
    snap = RuntimeSnapshot(cycle=7, phase="VALIDATE", capital=999.0)
    b.emit_snapshot(snap)
    env = b.replay.recent(n=1)[0]
    assert env.payload["type"] == "snapshot"
    assert env.payload["cycle"] == 7


def test_broker_emit_worker_health_has_worker_field():
    from backend.pubsub.broker import PubSubBroker
    b = PubSubBroker()
    b.emit_worker_health("feedback_worker", "ok", phase="EXPLORE")
    env = b.replay.recent(n=1)[0]
    assert env.payload["worker"] == "feedback_worker"
    assert env.payload["status"] == "ok"
    assert env.payload["phase"] == "EXPLORE"


def test_broker_emit_anomaly_shape():
    from backend.pubsub.broker import PubSubBroker
    from backend.events.schemas import ANOMALY_DETECTED
    b = PubSubBroker()
    b.emit_anomaly("error", "capital below threshold", source="risk_engine")
    env = b.replay.recent(n=1)[0]
    assert env.type == ANOMALY_DETECTED
    assert env.payload["level"] == "error"
    assert env.payload["message"] == "capital below threshold"


def test_broker_emit_decision_shape():
    from backend.pubsub.broker import PubSubBroker
    from backend.events.schemas import DECISION_LOGGED
    b = PubSubBroker()
    b.emit_decision("shoes", roas=2.1, label="WINNER", hook="urgency", angle="price")
    env = b.replay.recent(n=1)[0]
    assert env.type == DECISION_LOGGED
    assert env.payload["product"] == "shoes"
    assert env.payload["label"] == "WINNER"


def test_broker_emit_signals_updated():
    from backend.pubsub.broker import PubSubBroker
    from backend.events.schemas import SIGNALS_UPDATED
    b = PubSubBroker()
    sigs = [{"product": "shoes", "score": 0.9}]
    b.emit_signals_updated(sigs)
    env = b.replay.recent(n=1)[0]
    assert env.type == SIGNALS_UPDATED
    assert env.payload["count"] == 1


def test_broker_emit_simulation_completed():
    from backend.pubsub.broker import PubSubBroker
    from backend.events.schemas import SIMULATION_COMPLETED
    b = PubSubBroker()
    b.emit_simulation_completed(
        [{"rank": 1, "product": "shoes", "predicted_roas": 2.0}],
        top_product="shoes",
    )
    env = b.replay.recent(n=1)[0]
    assert env.type == SIMULATION_COMPLETED
    assert env.payload["top_product"] == "shoes"
    assert env.payload["signals_scored"] == 1


# ── Emitter helpers ───────────────────────────────────────────────────────────

def test_emitter_emit_tick_does_not_raise():
    from backend.events.emitter import emit_tick
    emit_tick("RESEARCH", avg_roas=1.0, capital=500.0)  # must not raise


def test_emitter_emit_snapshot_does_not_raise():
    from backend.events.emitter import emit_snapshot
    from backend.runtime.state import RuntimeSnapshot
    emit_snapshot(RuntimeSnapshot(cycle=1))


def test_emitter_emit_worker_health_does_not_raise():
    from backend.events.emitter import emit_worker_health
    emit_worker_health("signal_ingestion_worker", "ok", phase="RESEARCH")


def test_emitter_emit_anomaly_does_not_raise():
    from backend.events.emitter import emit_anomaly
    emit_anomaly("warning", "ROAS below floor", source="monitor")
