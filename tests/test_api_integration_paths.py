import asyncio

from fastapi.testclient import TestClient

from api.control import approve, get_control_snapshot, pause, reset_control_state
from api.main import app
from api.ws import event_stream
from core.control_state import load_control_state


def test_control_state_persists_flags():
    reset_control_state()
    approve("prod-a")
    pause("prod-a")

    snapshot = get_control_snapshot()
    loaded = load_control_state()
    assert "prod-a" in snapshot["approved_products"]
    assert "prod-a" in snapshot["paused_products"]
    assert "prod-a" in loaded["approved_products"]
    assert "prod-a" in loaded["paused_products"]


def test_queue_endpoints_return_serializable_payloads(monkeypatch):
    monkeypatch.delenv("UPOS_API_KEY", raising=False)
    monkeypatch.delenv("UPOS_EXEC_API_KEY", raising=False)
    monkeypatch.delenv("UPOS_CONTROL_API_KEY", raising=False)
    client = TestClient(app)

    class AsyncResultStub:
        id = "task-123"
        state = "PENDING"

    class DiscoveryTaskStub:
        @staticmethod
        def delay():
            return AsyncResultStub()

    class IntelligenceTaskStub:
        @staticmethod
        def delay(_keywords):
            return 2

    monkeypatch.setattr("api.main.run_discovery", DiscoveryTaskStub())
    monkeypatch.setattr("api.main.run_intelligence_pipeline", IntelligenceTaskStub())

    discovery = client.post("/run-discovery")
    assert discovery.status_code == 200
    assert discovery.json()["status"] == "queued"
    assert discovery.json()["task"]["id"] == "task-123"

    intelligence = client.post("/run-intelligence", json={"keywords": ["x"]})
    assert intelligence.status_code == 200
    assert intelligence.json()["status"] == "completed"
    assert intelligence.json()["result"] == 2


def test_readiness_check_returns_dependency_payload():
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert "db" in payload["checks"]
    assert "queue" in payload["checks"]
    assert "stream" in payload["checks"]


def test_websocket_stream_handles_disconnect_and_backpressure(monkeypatch):
    monkeypatch.delenv("UPOS_API_KEY", raising=False)
    monkeypatch.delenv("UPOS_EXEC_API_KEY", raising=False)
    class FakeWebSocket:
        def __init__(self):
            self.headers = {}
            self.query_params = {}
            self.sent = []
            self.closed = False

        async def accept(self):
            return None

        async def send_text(self, payload):
            self.sent.append(payload)

        async def close(self, code=1000):
            self.closed = True
            return None

    calls = {"count": 0}

    def consume_stub():
        calls["count"] += 1
        if calls["count"] == 1:
            return [("upos_events", [("1", {"data": "a"}), ("2", {"data": "b"}), ("3", {"data": "c"})])]
        return []

    monkeypatch.setattr("api.ws.consume", consume_stub)
    monkeypatch.setattr("api.ws.WS_MAX_MESSAGES_PER_TICK", 2)
    monkeypatch.setattr("api.ws.WS_MAX_EMPTY_POLLS", 1)
    monkeypatch.setattr("api.ws.WS_POLL_SLEEP_SECONDS", 0)
    monkeypatch.setattr("api.ws.WS_BACKPRESSURE_PAUSE_SECONDS", 0)

    ws = FakeWebSocket()
    asyncio.run(event_stream(ws))
    assert ws.sent == ["a", "b"]
    assert ws.closed is True
