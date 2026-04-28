"""Tests for backend.inference.embeddings — embedding pipeline."""
from __future__ import annotations

import pytest

from backend.inference.models.embedding_request import EmbeddingRequest, EmbeddingResponse
from backend.inference.providers.mock import MockProvider
from backend.inference.policies.routing_policy import RoutingPolicy
from backend.inference.router import InferenceRouter
from backend.inference.embeddings import (
    embed_texts,
    embed_text,
    embedding_replay_hash,
    clear_embedding_cache,
)


# ── EmbeddingRequest schema ───────────────────────────────────────────────────

def test_embedding_request_has_replay_hash():
    req = EmbeddingRequest(texts=["hello"])
    assert req.replay_hash is not None
    assert len(req.replay_hash) == 64


def test_embedding_request_to_dict_round_trip():
    req = EmbeddingRequest(texts=["a", "b"], model="em-model", provider="mock")
    d = req.to_dict()
    assert d["texts"] == ["a", "b"]
    assert d["model"] == "em-model"
    assert "replay_hash" in d
    assert "request_id" in d


def test_embedding_response_ok_true_on_success():
    resp = EmbeddingResponse(embeddings=[[0.1, 0.2]], request_id="r1")
    assert resp.ok is True


def test_embedding_response_ok_false_on_error():
    resp = EmbeddingResponse(error="boom")
    assert resp.ok is False


def test_embedding_response_to_dict():
    resp = EmbeddingResponse(
        request_id="r1",
        model="m",
        provider="mock",
        embeddings=[[0.1, 0.2]],
        latency_ms=5.0,
    )
    d = resp.to_dict()
    assert d["embeddings"] == [[0.1, 0.2]]
    assert d["latency_ms"] == 5.0


# ── MockProvider embeddings ───────────────────────────────────────────────────

def test_mock_embed_returns_correct_count():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["one", "two", "three"])
    resp = mp.embed(req)
    assert resp.ok
    assert len(resp.embeddings) == 3


def test_mock_embed_each_vector_has_4_dims():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["test"])
    resp = mp.embed(req)
    assert len(resp.embeddings[0]) == 4


def test_mock_embed_empty_texts_returns_empty():
    mp = MockProvider()
    req = EmbeddingRequest(texts=[])
    resp = mp.embed(req)
    assert resp.embeddings == []


def test_mock_embed_preserves_request_id():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["id test"])
    resp = mp.embed(req)
    assert resp.request_id == req.request_id


def test_mock_embed_preserves_sequence_id():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["seq"], sequence_id=77)
    resp = mp.embed(req)
    assert resp.sequence_id == 77


# ── InferenceRouter embedding routing ────────────────────────────────────────

def _mock_embed_router() -> InferenceRouter:
    policy = RoutingPolicy(default_order=["mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(MockProvider())
    return router


def test_router_embed_returns_embeddings():
    router = _mock_embed_router()
    req = EmbeddingRequest(texts=["route me"])
    resp = router.embed(req)
    assert resp.ok
    assert len(resp.embeddings) == 1


def test_router_embed_no_provider_returns_error():
    """Router with no embedding providers returns an error response."""
    from backend.inference.providers.base import BaseProvider

    class NoEmbedProvider(BaseProvider):
        name = "no_embed"
        supports_embeddings = False
        def complete(self, req): return self._make_error_response(req, self.name, "n/a")
        def health_check(self): return True

    policy = RoutingPolicy(default_order=["no_embed"])
    router = InferenceRouter(routing_policy=policy)
    router.register(NoEmbedProvider())

    req = EmbeddingRequest(texts=["nothing"])
    resp = router.embed(req)
    assert resp.ok is False
    assert resp.error == "no_embedding_provider_available"


# ── embed_texts / embed_text helpers ─────────────────────────────────────────

def test_embed_texts_returns_list_of_vectors(monkeypatch):
    """embed_texts uses inference_router — monkeypatch it to use mock."""
    import backend.inference.embeddings as emb_module
    import backend.inference.router as router_module

    mock_router = _mock_embed_router()
    monkeypatch.setattr(router_module, "inference_router", mock_router)

    clear_embedding_cache()
    vecs = embed_texts(["hello", "world"], provider="mock", use_cache=False)
    assert len(vecs) == 2
    assert all(isinstance(v, list) for v in vecs)


def test_embed_text_single_string(monkeypatch):
    import backend.inference.router as router_module

    mock_router = _mock_embed_router()
    monkeypatch.setattr(router_module, "inference_router", mock_router)

    clear_embedding_cache()
    vec = embed_text("single", provider="mock", use_cache=False)
    assert isinstance(vec, list)
    assert len(vec) > 0


def test_embed_texts_empty_input():
    clear_embedding_cache()
    result = embed_texts([])
    assert result == []


def test_embedding_replay_hash_deterministic():
    h1 = embedding_replay_hash(["a", "b"], model="m", provider="p")
    h2 = embedding_replay_hash(["a", "b"], model="m", provider="p")
    assert h1 == h2
    assert len(h1) == 64


def test_embedding_replay_hash_changes_with_texts():
    h1 = embedding_replay_hash(["x"])
    h2 = embedding_replay_hash(["y"])
    assert h1 != h2
