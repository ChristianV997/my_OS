"""Tests for backend.vector.embeddings — vector embedding bridge."""
from __future__ import annotations

import pytest

from backend.vector.embeddings import embed_for_index, embed_batch_for_index, embed_query
from backend.vector.schemas.vector_record import VectorRecord


def _make_mock_router():
    from backend.inference.providers.mock import MockProvider
    from backend.inference.policies.routing_policy import RoutingPolicy
    from backend.inference.router import InferenceRouter
    policy = RoutingPolicy(default_order=["mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(MockProvider())
    return router


# ── embed_for_index ───────────────────────────────────────────────────────────

def test_embed_for_index_returns_vector_record(monkeypatch):
    import backend.inference.router as router_module
    monkeypatch.setattr(router_module, "inference_router", _make_mock_router())
    from backend.inference.embeddings import clear_embedding_cache
    clear_embedding_cache()

    record = embed_for_index(
        text="test signal text",
        collection="signals",
        source_id="sig-001",
        source_type="signal",
        provider="mock",
        use_cache=False,
    )
    assert record is not None
    assert isinstance(record, VectorRecord)
    assert record.collection == "signals"
    assert record.source_id == "sig-001"
    assert record.source_type == "signal"
    assert len(record.vector) > 0


def test_embed_for_index_has_replay_hash(monkeypatch):
    import backend.inference.router as router_module
    monkeypatch.setattr(router_module, "inference_router", _make_mock_router())
    from backend.inference.embeddings import clear_embedding_cache
    clear_embedding_cache()

    record = embed_for_index(
        text="replay test",
        collection="signals",
        source_id="sig-002",
        source_type="signal",
        provider="mock",
        use_cache=False,
    )
    assert record is not None
    assert record.replay_hash is not None
    assert len(record.replay_hash) == 64


def test_embed_for_index_custom_replay_hash(monkeypatch):
    import backend.inference.router as router_module
    monkeypatch.setattr(router_module, "inference_router", _make_mock_router())
    from backend.inference.embeddings import clear_embedding_cache
    clear_embedding_cache()

    custom_hash = "a" * 64
    record = embed_for_index(
        text="hash test",
        collection="signals",
        source_id="sig-003",
        source_type="signal",
        provider="mock",
        use_cache=False,
        replay_hash=custom_hash,
    )
    assert record is not None
    assert record.replay_hash == custom_hash


# ── embed_batch_for_index ─────────────────────────────────────────────────────

def test_embed_batch_for_index_returns_records(monkeypatch):
    import backend.inference.router as router_module
    monkeypatch.setattr(router_module, "inference_router", _make_mock_router())
    from backend.inference.embeddings import clear_embedding_cache
    clear_embedding_cache()

    items = [
        {"text": "signal one", "source_id": "b1"},
        {"text": "signal two", "source_id": "b2"},
    ]
    records = embed_batch_for_index(
        items=items,
        collection="signals",
        source_type="signal",
        provider="mock",
        use_cache=False,
    )
    assert len(records) == 2
    assert all(isinstance(r, VectorRecord) for r in records)


def test_embed_batch_for_index_empty_input():
    records = embed_batch_for_index(
        items=[],
        collection="signals",
        source_type="signal",
    )
    assert records == []


# ── embed_query ───────────────────────────────────────────────────────────────

def test_embed_query_returns_vector(monkeypatch):
    import backend.inference.router as router_module
    monkeypatch.setattr(router_module, "inference_router", _make_mock_router())
    from backend.inference.embeddings import clear_embedding_cache
    clear_embedding_cache()

    vec = embed_query("market trends", provider="mock", use_cache=False)
    assert isinstance(vec, list)
    assert len(vec) > 0
