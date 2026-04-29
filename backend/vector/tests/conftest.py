"""Shared fixtures for vector tests — always uses InMemoryVectorStore."""
import pytest

from backend.vector.qdrant_client import InMemoryVectorStore, reset_store
from backend.vector.collections   import ALL_COLLECTIONS
from backend.vector.normalization  import normalize


@pytest.fixture(autouse=True)
def fresh_store():
    """Inject a clean InMemoryVectorStore before every test."""
    from backend.vector.qdrant_client import get_spec
    store = InMemoryVectorStore()
    for name in ALL_COLLECTIONS:
        from backend.vector.collections import get_spec as _gs
        store.ensure_collection(_gs(name))
    reset_store(store)
    yield store
    reset_store(None)


@pytest.fixture(autouse=True)
def mock_inference(monkeypatch):
    """Force all embedding calls through MockProvider."""
    from backend.inference.router    import InferenceRouter
    from backend.inference.providers.mock import MockProvider
    import backend.inference.router as rm
    monkeypatch.setattr(rm, "_router", InferenceRouter(providers=[MockProvider()]))
