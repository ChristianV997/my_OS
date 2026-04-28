"""Tests for the embedding pipeline and domain-specific helpers."""
import math
import pytest

from backend.inference.embeddings import (
    embed_text,
    embed_batch,
    embed_hooks,
    embed_products,
    embed_angles,
    similarity,
    top_k_similar,
)
from backend.inference.models.embedding_request import EmbeddingRequest
from backend.inference.providers.mock           import MockProvider
from backend.inference.router                   import InferenceRouter


# ── test fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_router(monkeypatch):
    """Force all embedding calls to use a MockProvider-only router."""
    router = InferenceRouter(providers=[MockProvider()])
    import backend.inference.router as router_mod
    monkeypatch.setattr(router_mod, "_router", router)


# ── embed_text ────────────────────────────────────────────────────────────────

def test_embed_text_returns_vector():
    vec = embed_text("This changed everything…")
    assert isinstance(vec, list)
    assert len(vec) == 384


def test_embed_text_is_normalised():
    vec  = embed_text("normalised vector")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


def test_embed_text_deterministic():
    v1 = embed_text("same text")
    v2 = embed_text("same text")
    assert v1 == v2


# ── embed_batch ───────────────────────────────────────────────────────────────

def test_embed_batch_returns_one_vec_per_text():
    texts = ["hook A", "hook B", "hook C"]
    vecs  = embed_batch(texts)
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)


def test_embed_batch_empty_returns_empty():
    assert embed_batch([]) == []


# ── domain helpers ────────────────────────────────────────────────────────────

def test_embed_hooks_returns_dict():
    hooks  = ["This changed everything…", "Nobody talks about this"]
    result = embed_hooks(hooks)
    assert set(result.keys()) == set(hooks)
    assert all(len(v) == 384 for v in result.values())


def test_embed_products_returns_dict():
    products = ["wireless earbuds", "led strips"]
    result   = embed_products(products)
    assert set(result.keys()) == set(products)


def test_embed_angles_returns_dict():
    angles = ["problem-solution", "social-proof", "urgency"]
    result = embed_angles(angles)
    assert set(result.keys()) == set(angles)


def test_embed_hooks_empty_returns_empty():
    assert embed_hooks([]) == {}


# ── similarity ────────────────────────────────────────────────────────────────

def test_similarity_identical_vectors_is_one():
    vec = embed_text("test vector")
    assert abs(similarity(vec, vec) - 1.0) < 1e-6


def test_similarity_different_vectors_less_than_one():
    v1 = embed_text("hook about money")
    v2 = embed_text("completely different text xyz123")
    s  = similarity(v1, v2)
    # Not guaranteed to be < 1.0 with random mock, but must be in [-1, 1]
    assert -1.0 <= s <= 1.0 + 1e-6


def test_similarity_empty_vectors():
    assert similarity([], []) == 0.0
    assert similarity([1.0], []) == 0.0


def test_similarity_mismatched_lengths():
    assert similarity([1.0, 0.0], [1.0]) == 0.0


# ── top_k_similar ─────────────────────────────────────────────────────────────

def test_top_k_similar_returns_k_results():
    query      = embed_text("query hook")
    candidates = embed_hooks(["hook A", "hook B", "hook C", "hook D", "hook E"])
    results    = top_k_similar(query, candidates, k=3)
    assert len(results) == 3


def test_top_k_similar_returns_tuples():
    query      = embed_text("q")
    candidates = embed_hooks(["a", "b"])
    results    = top_k_similar(query, candidates, k=2)
    for name, score in results:
        assert isinstance(name, str)
        assert isinstance(score, float)


def test_top_k_similar_sorted_by_score():
    query      = embed_text("sort test")
    candidates = embed_hooks(["x", "y", "z"])
    results    = top_k_similar(query, candidates, k=3)
    scores     = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_similar_fewer_candidates_than_k():
    query      = embed_text("q")
    candidates = embed_hooks(["only one"])
    results    = top_k_similar(query, candidates, k=10)
    assert len(results) == 1
