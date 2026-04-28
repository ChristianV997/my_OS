"""Tests for determinism and replay safety.

Critical invariants:
  1. Same sequence_id → same content (cached response)
  2. Same prompt hash → same mock content (deterministic mock)
  3. replay_hash is content-based, not sequence_id-based
  4. Two requests with identical content but different sequence_ids get
     the same replay_hash
"""
import pytest

from backend.inference._utils import compute_replay_hash
from backend.inference.models.inference_request  import InferenceRequest
from backend.inference.models.embedding_request  import EmbeddingRequest
from backend.inference.providers.mock            import MockProvider
from backend.inference.router                    import InferenceRouter


# ── replay hash ───────────────────────────────────────────────────────────────

def test_replay_hash_same_for_identical_prompts():
    r1 = InferenceRequest(prompt="hello world", temperature=0.7, sequence_id="a1")
    r2 = InferenceRequest(prompt="hello world", temperature=0.7, sequence_id="a2")
    assert compute_replay_hash(r1) == compute_replay_hash(r2)


def test_replay_hash_differs_for_different_prompts():
    r1 = InferenceRequest(prompt="hello world")
    r2 = InferenceRequest(prompt="goodbye world")
    assert compute_replay_hash(r1) != compute_replay_hash(r2)


def test_replay_hash_differs_for_different_temperature():
    r1 = InferenceRequest(prompt="same", temperature=0.0)
    r2 = InferenceRequest(prompt="same", temperature=1.0)
    assert compute_replay_hash(r1) != compute_replay_hash(r2)


def test_replay_hash_differs_for_different_seed():
    r1 = InferenceRequest(prompt="same", seed=42)
    r2 = InferenceRequest(prompt="same", seed=99)
    assert compute_replay_hash(r1) != compute_replay_hash(r2)


def test_replay_hash_is_16_hex_chars():
    req  = InferenceRequest(prompt="check length")
    h    = compute_replay_hash(req)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


# ── cached replay ─────────────────────────────────────────────────────────────

def test_same_sequence_id_returns_cached_response():
    router = InferenceRouter(providers=[MockProvider()])
    seq_id = "det-replay-001"
    req    = InferenceRequest(prompt="determinism test", sequence_id=seq_id)

    resp1 = router.complete(req)
    resp2 = router.complete(req)

    assert resp1.content == resp2.content
    assert resp2.replayed is True or resp2.cached is True


def test_cached_response_has_same_replay_hash():
    router = InferenceRouter(providers=[MockProvider()])
    req    = InferenceRequest(prompt="replay hash check", sequence_id="det-002")
    r1     = router.complete(req)
    r2     = router.complete(req)
    assert r1.replay_hash == r2.replay_hash


def test_different_sequence_ids_produce_independent_responses():
    router = InferenceRouter(providers=[MockProvider()])
    r1 = router.complete(InferenceRequest(prompt="prompt A", sequence_id="ind-001"))
    r2 = router.complete(InferenceRequest(prompt="prompt B", sequence_id="ind-002"))
    # Both should succeed
    assert r1.ok
    assert r2.ok
    # Different sequence IDs → independent cache entries
    assert router.cache_size() == 2


# ── mock determinism ──────────────────────────────────────────────────────────

def test_mock_same_prompt_always_same_content():
    mock   = MockProvider()
    prompt = "consistent mock output"
    req1   = InferenceRequest(prompt=prompt, sequence_id="m1")
    req2   = InferenceRequest(prompt=prompt, sequence_id="m2")

    r1 = mock.complete(req1)
    r2 = mock.complete(req2)
    assert r1.content == r2.content


def test_mock_different_prompts_may_differ():
    mock = MockProvider()
    r1   = mock.complete(InferenceRequest(prompt="aaa"))
    r2   = mock.complete(InferenceRequest(prompt="zzz"))
    # Content is picked by hash mod — may collide but usually won't
    assert r1.content or r2.content  # at least one is non-empty


# ── embedding determinism ─────────────────────────────────────────────────────

def test_mock_embedding_same_text_same_vector():
    mock  = MockProvider()
    text  = "deterministic embedding test"
    req1  = EmbeddingRequest(texts=[text])
    req2  = EmbeddingRequest(texts=[text])
    vecs1 = mock.embed(req1)
    vecs2 = mock.embed(req2)
    assert vecs1 == vecs2


def test_mock_embedding_different_texts_different_vectors():
    mock  = MockProvider()
    req   = EmbeddingRequest(texts=["text A", "text B"])
    vecs  = mock.embed(req)
    assert vecs[0] != vecs[1]
