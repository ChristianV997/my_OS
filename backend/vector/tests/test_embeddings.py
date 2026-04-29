"""Tests for the vector embedding cache wrapper."""
import pytest

from backend.vector.embeddings import (
    embed_text, embed_batch, embed_dict, cache_size, clear_cache,
)


@pytest.fixture(autouse=True)
def reset_embed_cache():
    clear_cache()
    yield
    clear_cache()


def test_embed_text_returns_384_dim_vector():
    vec = embed_text("test hook text")
    assert isinstance(vec, list)
    assert len(vec) == 384


def test_embed_text_is_normalized():
    import math
    vec = embed_text("normalized test")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


def test_embed_text_cached_on_second_call():
    embed_text("cache me")
    before = cache_size()
    embed_text("cache me")
    after = cache_size()
    assert before == after  # no new entry


def test_embed_text_cache_grows():
    clear_cache()
    embed_text("text A")
    assert cache_size() == 1
    embed_text("text B")
    assert cache_size() == 2


def test_embed_batch_returns_correct_count():
    vecs = embed_batch(["alpha", "beta", "gamma"])
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)


def test_embed_batch_empty():
    assert embed_batch([]) == []


def test_embed_batch_uses_cache():
    embed_text("shared text")
    before = cache_size()
    embed_batch(["shared text", "new text"])
    # "shared text" cached; only "new text" is new
    assert cache_size() == before + 1


def test_embed_dict_keys_are_preserved():
    d = {"hook A": 1, "hook B": 2}
    result = embed_dict(d)
    assert set(result.keys()) == {"hook A", "hook B"}
    assert all(len(v) == 384 for v in result.values())


def test_clear_cache():
    embed_text("x")
    embed_text("y")
    clear_cache()
    assert cache_size() == 0
