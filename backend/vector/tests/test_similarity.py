"""Tests for similarity utilities."""
import math
import pytest

from backend.vector.similarity import cosine, dot_product, batch_cosine, affinity_matrix, top_k
from backend.vector.normalization import normalize


def _unit(dim=4, seed=1):
    import random
    rng = random.Random(seed)
    v = [rng.gauss(0, 1) for _ in range(dim)]
    return normalize(v)


def test_cosine_identical():
    v = _unit()
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(cosine(a, b)) < 1e-9


def test_cosine_dimension_mismatch_returns_zero():
    assert cosine([1.0, 2.0], [1.0]) == 0.0


def test_cosine_empty_returns_zero():
    assert cosine([], []) == 0.0


def test_dot_product_basic():
    assert abs(dot_product([1.0, 2.0], [3.0, 4.0]) - 11.0) < 1e-9


def test_batch_cosine_length():
    q = _unit()
    cs = [_unit(seed=i) for i in range(5)]
    scores = batch_cosine(q, cs)
    assert len(scores) == 5
    assert all(-1.0 <= s <= 1.0 + 1e-6 for s in scores)


def test_affinity_matrix_symmetric():
    vecs = [_unit(seed=i) for i in range(3)]
    m = affinity_matrix(vecs)
    assert len(m) == 3
    assert len(m[0]) == 3
    for i in range(3):
        for j in range(3):
            assert abs(m[i][j] - m[j][i]) < 1e-9


def test_affinity_matrix_diagonal_is_one():
    vecs = [_unit(seed=i) for i in range(3)]
    m = affinity_matrix(vecs)
    for i in range(3):
        assert abs(m[i][i] - 1.0) < 1e-6


def test_top_k_returns_k_results():
    q = _unit()
    candidates = {f"item_{i}": _unit(seed=i + 10) for i in range(8)}
    results = top_k(q, candidates, k=3)
    assert len(results) == 3


def test_top_k_sorted_descending():
    q = _unit()
    candidates = {f"item_{i}": _unit(seed=i + 20) for i in range(6)}
    results = top_k(q, candidates, k=6)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_threshold_filter():
    q = _unit()
    candidates = {f"item_{i}": _unit(seed=i + 30) for i in range(10)}
    results = top_k(q, candidates, k=10, threshold=0.99)
    # All returned must meet threshold
    for _, score in results:
        assert score >= 0.99
