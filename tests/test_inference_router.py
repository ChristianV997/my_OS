"""Tests for backend.inference.router — centralized inference routing kernel."""
from __future__ import annotations

import pytest

from backend.inference.models.inference_request import InferenceRequest
from backend.inference.models.inference_response import InferenceResponse
from backend.inference.models.embedding_request import EmbeddingRequest
from backend.inference.providers.mock import MockProvider
from backend.inference.policies.routing_policy import RoutingPolicy
from backend.inference.policies.fallback_policy import FallbackPolicy
from backend.inference.router import InferenceRouter


# ── helpers ───────────────────────────────────────────────────────────────────

def _router_with_mock() -> InferenceRouter:
    policy = RoutingPolicy(default_order=["mock"])
    router = InferenceRouter(routing_policy=policy)
    router.register(MockProvider())
    return router


def _router_with_failing_then_mock() -> InferenceRouter:
    """Router where first provider always fails, second is mock."""
    from backend.inference.providers.base import BaseProvider

    class AlwaysFailProvider(BaseProvider):
        name = "always_fail"
        supports_streaming = False

        def complete(self, request):
            return self._make_error_response(request, self.name, "intentional_failure")

        def health_check(self):
            return True

    policy = RoutingPolicy(default_order=["always_fail", "mock"])
    router = InferenceRouter(
        routing_policy=policy,
        fallback_policy=FallbackPolicy(max_retries=2),
    )
    router.register(AlwaysFailProvider())
    router.register(MockProvider())
    return router


# ── InferenceRequest schema ───────────────────────────────────────────────────

def test_inference_request_auto_replay_hash():
    req = InferenceRequest(prompt="hello")
    assert req.replay_hash is not None
    assert len(req.replay_hash) == 64  # sha256 hex


def test_inference_request_deterministic_hash():
    req1 = InferenceRequest(prompt="test", model="gpt-4o-mini", temperature=0.5)
    req2 = InferenceRequest(prompt="test", model="gpt-4o-mini", temperature=0.5)
    assert req1.replay_hash == req2.replay_hash


def test_inference_request_different_prompts_different_hash():
    req1 = InferenceRequest(prompt="hello")
    req2 = InferenceRequest(prompt="world")
    assert req1.replay_hash != req2.replay_hash


def test_inference_request_to_dict_round_trip():
    req = InferenceRequest(prompt="p", model="m", provider="openai", max_tokens=100)
    d = req.to_dict()
    assert d["prompt"] == "p"
    assert d["model"] == "m"
    assert d["provider"] == "openai"
    assert d["max_tokens"] == 100
    assert "replay_hash" in d
    assert "request_id" in d


# ── InferenceResponse schema ──────────────────────────────────────────────────

def test_inference_response_ok_true_when_no_error():
    from backend.inference.models.inference_response import InferenceResponse
    resp = InferenceResponse(request_id="r1", text="hi", provider="mock")
    assert resp.ok is True


def test_inference_response_ok_false_when_error():
    from backend.inference.models.inference_response import InferenceResponse
    resp = InferenceResponse(request_id="r1", error="fail")
    assert resp.ok is False


def test_inference_response_to_dict_has_expected_keys():
    from backend.inference.models.inference_response import InferenceResponse, TokenUsage
    resp = InferenceResponse(
        request_id="r1",
        model="gpt",
        provider="openai",
        text="result",
        usage=TokenUsage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
    )
    d = resp.to_dict()
    assert d["text"] == "result"
    assert d["usage"]["total_tokens"] == 8
    assert d["fallback_used"] is False


# ── MockProvider ──────────────────────────────────────────────────────────────

def test_mock_provider_complete_succeeds():
    mp = MockProvider()
    req = InferenceRequest(prompt="test prompt")
    resp = mp.complete(req)
    assert resp.ok
    assert "mock" in resp.text
    assert resp.provider == "mock"


def test_mock_provider_preserves_request_id():
    mp = MockProvider()
    req = InferenceRequest(prompt="hello")
    resp = mp.complete(req)
    assert resp.request_id == req.request_id


def test_mock_provider_preserves_replay_hash():
    mp = MockProvider()
    req = InferenceRequest(prompt="deterministic")
    resp = mp.complete(req)
    assert resp.replay_hash == req.replay_hash


def test_mock_provider_embed_returns_vectors():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["hello", "world"])
    resp = mp.embed(req)
    assert resp.ok
    assert len(resp.embeddings) == 2
    assert len(resp.embeddings[0]) == 4  # mock returns 4-element vectors


def test_mock_provider_embed_deterministic():
    mp = MockProvider()
    req = EmbeddingRequest(texts=["test_text"])
    resp1 = mp.embed(req)
    resp2 = mp.embed(req)
    assert resp1.embeddings == resp2.embeddings


# ── InferenceRouter ───────────────────────────────────────────────────────────

def test_router_complete_with_mock_provider():
    router = _router_with_mock()
    req = InferenceRequest(prompt="hello router")
    resp = router.complete(req)
    assert resp.ok
    assert resp.provider == "mock"


def test_router_complete_preserves_sequence_id():
    router = _router_with_mock()
    req = InferenceRequest(prompt="sequence test", sequence_id=999)
    resp = router.complete(req)
    assert resp.sequence_id == 999


def test_router_complete_preserves_correlation_id():
    router = _router_with_mock()
    req = InferenceRequest(prompt="corr", correlation_id="corr-abc")
    resp = router.complete(req)
    assert resp.correlation_id == "corr-abc"


def test_router_fallback_to_mock_when_primary_fails():
    router = _router_with_failing_then_mock()
    req = InferenceRequest(prompt="fallback test", provider="auto")
    resp = router.complete(req)
    assert resp.ok
    assert resp.provider == "mock"
    assert resp.fallback_used is True
    assert "always_fail" in resp.fallback_chain


def test_router_fallback_chain_recorded_in_response():
    router = _router_with_failing_then_mock()
    req = InferenceRequest(prompt="chain test")
    resp = router.complete(req)
    assert len(resp.fallback_chain) >= 2


def test_router_explicit_provider_hint_respected():
    router = _router_with_mock()
    req = InferenceRequest(prompt="hint test", provider="mock")
    resp = router.complete(req)
    assert resp.provider == "mock"


def test_router_embed_with_mock():
    router = _router_with_mock()
    req = EmbeddingRequest(texts=["embed me"])
    resp = router.embed(req)
    assert resp.ok
    assert len(resp.embeddings) == 1


# ── RoutingPolicy ─────────────────────────────────────────────────────────────

def test_routing_policy_selects_healthy_provider():
    mp = MockProvider()
    policy = RoutingPolicy(default_order=["mock"])
    policy.register(mp)
    req = InferenceRequest(prompt="p")
    decision = policy.decide(req)
    assert decision.selected_provider == "mock"


def test_routing_policy_respects_explicit_provider():
    mp = MockProvider()
    policy = RoutingPolicy(default_order=["mock"])
    policy.register(mp)
    req = InferenceRequest(prompt="p", provider="mock")
    decision = policy.decide(req)
    assert decision.selected_provider == "mock"
    assert decision.reason == "explicit_provider_hint"


def test_routing_policy_decision_preserves_replay_hash():
    mp = MockProvider()
    policy = RoutingPolicy(default_order=["mock"])
    policy.register(mp)
    req = InferenceRequest(prompt="hash test")
    decision = policy.decide(req)
    assert decision.replay_hash == req.replay_hash


# ── FallbackPolicy ────────────────────────────────────────────────────────────

def test_fallback_policy_triggers_on_error():
    from backend.inference.models.inference_response import InferenceResponse
    policy = FallbackPolicy(max_retries=2)
    resp = InferenceResponse(error="boom")
    assert policy.should_fallback(resp, attempt=0) is True


def test_fallback_policy_stops_at_max_retries():
    from backend.inference.models.inference_response import InferenceResponse
    policy = FallbackPolicy(max_retries=2)
    resp = InferenceResponse(error="boom")
    assert policy.should_fallback(resp, attempt=2) is False


def test_fallback_policy_no_fallback_on_success():
    from backend.inference.models.inference_response import InferenceResponse
    policy = FallbackPolicy()
    resp = InferenceResponse(text="great success")
    assert policy.should_fallback(resp, attempt=0) is False


def test_fallback_policy_retry_on_empty():
    from backend.inference.models.inference_response import InferenceResponse
    policy = FallbackPolicy(retry_on_empty=True)
    resp = InferenceResponse(text="")
    assert policy.should_fallback(resp, attempt=0) is True


# ── async streaming ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_stream_yields_tokens():
    router = _router_with_mock()
    req = InferenceRequest(prompt="stream this", stream=True)
    tokens = []
    async for token in router.stream(req):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens)
    assert len(full) > 0


@pytest.mark.asyncio
async def test_mock_provider_stream_yields_tokens():
    mp = MockProvider()
    req = InferenceRequest(prompt="stream me")
    tokens = []
    async for token in mp.stream(req):
        tokens.append(token)
    assert len(tokens) > 0
