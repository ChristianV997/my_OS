"""Shared fixtures for sleep runtime tests."""
import pytest

from backend.vector.qdrant_client import InMemoryVectorStore, reset_store
from backend.vector.collections   import ALL_COLLECTIONS


@pytest.fixture(autouse=True)
def fresh_vector_store():
    from backend.vector.collections import get_spec
    store = InMemoryVectorStore()
    for name in ALL_COLLECTIONS:
        store.ensure_collection(get_spec(name))
    reset_store(store)
    yield store
    reset_store(None)


@pytest.fixture(autouse=True)
def mock_inference(monkeypatch):
    from backend.inference.router        import InferenceRouter
    from backend.inference.providers.mock import MockProvider
    import backend.inference.router as rm
    monkeypatch.setattr(rm, "_router", InferenceRouter(providers=[MockProvider()]))


@pytest.fixture()
def small_batch():
    """A minimal ReplayBatch with a few synthetic events."""
    import time, uuid
    from backend.runtime.sleep.schemas.replay_batch import ReplayBatch
    now = time.time()
    events = [
        {"type": "decision.logged",  "hook": "This changed everything",
         "angle": "problem-solution", "product": "earbuds", "roas": 2.5,
         "ts": now - 100},
        {"type": "decision.logged",  "hook": "Nobody talks about this",
         "angle": "social-proof",    "product": "earbuds", "roas": 3.1,
         "ts": now - 50},
        {"type": "campaign.launched", "hook": "Wait for it",
         "angle": "urgency",          "product": "led strips", "roas": 0.0,
         "ts": now - 10},
        {"type": "signals.updated",  "signals": [
            {"keyword": "morning routine", "type": "trend"},
            {"keyword": "productivity hack", "type": "trend"},
        ], "ts": now - 200},
    ]
    return ReplayBatch(
        batch_id=uuid.uuid4().hex[:12],
        workspace="test",
        start_ts=now - 300,
        end_ts=now,
        events=events,
        source="test",
    )
