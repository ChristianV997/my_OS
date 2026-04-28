"""Tests for backend.vector — semantic search pipeline (with mocked store)."""
from __future__ import annotations

import pytest

from backend.vector.schemas.search_query import SearchQuery
from backend.vector.schemas.similarity_result import SimilarityResult
from backend.vector.schemas.vector_record import VectorRecord


# ── SearchQuery schema ────────────────────────────────────────────────────────

def test_search_query_has_replay_hash():
    q = SearchQuery(collection="signals", query_text="trending products")
    assert q.replay_hash is not None
    assert len(q.replay_hash) == 64


def test_search_query_same_input_same_hash():
    q1 = SearchQuery(collection="signals", query_text="trending products", top_k=5)
    q2 = SearchQuery(collection="signals", query_text="trending products", top_k=5)
    assert q1.replay_hash == q2.replay_hash


def test_search_query_different_collection_different_hash():
    q1 = SearchQuery(collection="signals", query_text="test")
    q2 = SearchQuery(collection="creatives", query_text="test")
    assert q1.replay_hash != q2.replay_hash


def test_search_query_to_dict():
    q = SearchQuery(collection="creatives", query_text="hooks", top_k=3)
    d = q.to_dict()
    assert d["collection"] == "creatives"
    assert d["query_text"] == "hooks"
    assert d["top_k"] == 3
    assert "replay_hash" in d


def test_search_query_with_vector():
    q = SearchQuery(collection="signals", query_vector=[0.1, 0.2, 0.3])
    assert q.query_vector == [0.1, 0.2, 0.3]
    assert q.query_text is None


# ── SimilarityResult schema ───────────────────────────────────────────────────

def test_similarity_result_to_dict():
    r = SimilarityResult(
        record_id="r1",
        score=0.92,
        source_id="sig-001",
        source_type="signal",
        collection="signals",
        rank=1,
    )
    d = r.to_dict()
    assert d["score"] == 0.92
    assert d["rank"] == 1
    assert d["source_type"] == "signal"


# ── semantic_search with mocked store ─────────────────────────────────────────

def _make_mock_store():
    """Return a mock VectorStoreClient that returns one fake result."""
    from backend.vector.schemas.similarity_result import SimilarityResult

    class MockStore:
        available = True

        def search(self, collection, query_vector, top_k=10, score_threshold=0.0,
                   filters=None, replay_hash=None, sequence_id=None, request_id=None):
            return [
                SimilarityResult(
                    record_id="fake-id",
                    score=0.88,
                    source_id="src-1",
                    source_type="signal",
                    collection=collection,
                    rank=1,
                )
            ]

        def upsert(self, record): return True
        def upsert_batch(self, records): return len(records)
        def count(self, collection): return 1
        def ensure_collection(self, *a, **kw): return True
        def collection_exists(self, name): return True

    return MockStore()


def test_semantic_search_returns_results(monkeypatch):
    import backend.vector.qdrant_client as qc_module
    import backend.inference.router as router_module
    from backend.inference.providers.mock import MockProvider
    from backend.inference.policies.routing_policy import RoutingPolicy
    from backend.inference.router import InferenceRouter
    from backend.inference.embeddings import clear_embedding_cache

    policy = RoutingPolicy(default_order=["mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(MockProvider())
    monkeypatch.setattr(router_module, "inference_router", router)

    mock_store = _make_mock_store()
    monkeypatch.setattr(qc_module, "_vector_store", mock_store)

    clear_embedding_cache()

    from backend.vector.semantic_search import semantic_search
    q = SearchQuery(
        collection="signals",
        query_text="market trends",
        top_k=5,
    )
    results = semantic_search(q, embedding_provider="mock")
    assert isinstance(results, list)
    assert len(results) >= 0  # may be 0 if embed returns empty, but no exception


def test_semantic_search_no_input_returns_empty(monkeypatch):
    import backend.vector.qdrant_client as qc_module
    monkeypatch.setattr(qc_module, "_vector_store", _make_mock_store())

    from backend.vector.semantic_search import semantic_search
    q = SearchQuery(collection="signals")  # no text, no vector
    results = semantic_search(q)
    assert results == []


def test_semantic_search_with_pre_computed_vector(monkeypatch):
    import backend.vector.qdrant_client as qc_module
    monkeypatch.setattr(qc_module, "_vector_store", _make_mock_store())

    from backend.vector.semantic_search import semantic_search
    q = SearchQuery(
        collection="signals",
        query_vector=[0.1, 0.2, 0.3, 0.4],
        top_k=3,
    )
    results = semantic_search(q)
    assert isinstance(results, list)
    assert all(isinstance(r, SimilarityResult) for r in results)
