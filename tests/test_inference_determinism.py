"""Tests for backend.inference — deterministic replay and hash consistency."""
from __future__ import annotations

import hashlib
import json

import pytest

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.embedding_request import EmbeddingRequest
from backend.inference.providers.mock import MockProvider
from backend.inference.policies.routing_policy import RoutingPolicy
from backend.inference.router import InferenceRouter


# ── replay hash determinism ───────────────────────────────────────────────────

def test_same_request_same_replay_hash():
    req1 = InferenceRequest(prompt="identical", model="gpt-4", temperature=0.7)
    req2 = InferenceRequest(prompt="identical", model="gpt-4", temperature=0.7)
    assert req1.replay_hash == req2.replay_hash


def test_different_prompt_different_replay_hash():
    req1 = InferenceRequest(prompt="prompt A")
    req2 = InferenceRequest(prompt="prompt B")
    assert req1.replay_hash != req2.replay_hash


def test_replay_hash_format_is_sha256_hex():
    req = InferenceRequest(prompt="hash format test")
    assert len(req.replay_hash) == 64
    int(req.replay_hash, 16)  # should not raise


def test_replay_hash_matches_manual_computation():
    """Verify the hash algorithm is exactly sha256 over a sorted canonical dict."""
    req = InferenceRequest(
        prompt="canonical",
        model="m",
        provider="p",
        system_prompt="sys",
        messages=[],
        temperature=None,
        max_tokens=None,
    )
    canonical = {
        "model": "m",
        "provider": "p",
        "prompt": "canonical",
        "system_prompt": "sys",
        "messages": [],
        "temperature": None,
        "max_tokens": None,
    }
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert req.replay_hash == expected


def test_embedding_request_replay_hash_deterministic():
    req1 = EmbeddingRequest(texts=["a", "b"], model="em", provider="auto")
    req2 = EmbeddingRequest(texts=["a", "b"], model="em", provider="auto")
    assert req1.replay_hash == req2.replay_hash


def test_embedding_request_different_texts_different_hash():
    req1 = EmbeddingRequest(texts=["text one"])
    req2 = EmbeddingRequest(texts=["text two"])
    assert req1.replay_hash != req2.replay_hash


# ── mock provider determinism ─────────────────────────────────────────────────

def test_mock_provider_same_request_same_output():
    mp = MockProvider()
    req1 = InferenceRequest(prompt="deterministic")
    req2 = InferenceRequest(prompt="deterministic")
    # Request IDs will differ, but replay hashes match
    assert req1.replay_hash == req2.replay_hash
    resp1 = mp.complete(req1)
    resp2 = mp.complete(req2)
    # Both responses reflect the same replay_hash
    assert resp1.replay_hash == resp2.replay_hash
    # text uses replay_hash so must match
    assert resp1.text == resp2.text


def test_mock_embed_same_text_same_vector():
    mp = MockProvider()
    r1 = EmbeddingRequest(texts=["test"])
    r2 = EmbeddingRequest(texts=["test"])
    resp1 = mp.embed(r1)
    resp2 = mp.embed(r2)
    assert resp1.embeddings == resp2.embeddings


def test_mock_embed_different_text_different_vector():
    mp = MockProvider()
    r1 = EmbeddingRequest(texts=["alpha"])
    r2 = EmbeddingRequest(texts=["beta"])
    resp1 = mp.embed(r1)
    resp2 = mp.embed(r2)
    assert resp1.embeddings != resp2.embeddings


# ── sequence_id ordering ──────────────────────────────────────────────────────

def test_response_preserves_sequence_id():
    mp = MockProvider()
    req = InferenceRequest(prompt="seq", sequence_id=42)
    resp = mp.complete(req)
    assert resp.sequence_id == 42


def test_response_sequence_id_none_when_not_set():
    mp = MockProvider()
    req = InferenceRequest(prompt="no seq")
    resp = mp.complete(req)
    assert resp.sequence_id is None


# ── routing decision replay fields ────────────────────────────────────────────

def test_routing_decision_carries_replay_hash():
    mp = MockProvider()
    policy = RoutingPolicy(default_order=["mock"])
    policy.register(mp)
    req = InferenceRequest(prompt="routing hash test", sequence_id=7)
    decision = policy.decide(req)
    assert decision.replay_hash == req.replay_hash
    assert decision.sequence_id == 7


# ── router preserves deterministic fields end-to-end ─────────────────────────

def test_router_end_to_end_determinism():
    policy = RoutingPolicy(default_order=["mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(MockProvider())

    req1 = InferenceRequest(prompt="deterministic end to end", model="default")
    req2 = InferenceRequest(prompt="deterministic end to end", model="default")

    assert req1.replay_hash == req2.replay_hash

    resp1 = router.complete(req1)
    resp2 = router.complete(req2)

    assert resp1.replay_hash == resp2.replay_hash
    assert resp1.text == resp2.text
    assert resp1.provider == resp2.provider


# ── fallback chain determinism ────────────────────────────────────────────────

def test_fallback_chain_order_is_deterministic():
    """Fallback order must be stable across multiple routing decisions."""
    from backend.inference.providers.base import BaseProvider
    from backend.inference.models.inference_response import InferenceResponse

    class FailProvider(BaseProvider):
        name = "fail_a"
        def complete(self, req): return self._make_error_response(req, self.name, "fail")
        def health_check(self): return True

    policy = RoutingPolicy(default_order=["fail_a", "mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(FailProvider())
    router.register(MockProvider())

    req1 = InferenceRequest(prompt="chain order 1")
    req2 = InferenceRequest(prompt="chain order 2")

    resp1 = router.complete(req1)
    resp2 = router.complete(req2)

    assert resp1.fallback_chain == resp2.fallback_chain
