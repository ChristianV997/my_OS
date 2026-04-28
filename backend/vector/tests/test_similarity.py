"""Tests for backend.vector.similarity — cosine similarity operations."""
from __future__ import annotations

import math
import pytest

from backend.vector.similarity import (
    cosine_similarity,
    dot_product,
    cosine_similarity_normalized,
    top_k_similar,
    pairwise_similarity_matrix,
)
from backend.vector.normalization import normalize


# ── cosine_similarity ─────────────────────────────────────────────────────────

def test_identical_vectors_similarity_one():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_orthogonal_vectors_similarity_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_opposite_vectors_similarity_minus_one():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_zero_vector_returns_zero():
    zero = [0.0, 0.0]
    v = [1.0, 0.0]
    assert cosine_similarity(zero, v) == 0.0
    assert cosine_similarity(v, zero) == 0.0


def test_mismatched_dim_returns_zero():
    a = [1.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_empty_vector_returns_zero():
    assert cosine_similarity([], []) == 0.0


def test_similarity_symmetric():
    a = [0.3, 0.7, 0.1]
    b = [0.5, 0.2, 0.9]
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


# ── dot_product ───────────────────────────────────────────────────────────────

def test_dot_product_basic():
    a = [1.0, 2.0, 3.0]
    b = [4.0, 5.0, 6.0]
    assert dot_product(a, b) == pytest.approx(32.0)


def test_dot_product_empty():
    assert dot_product([], []) == 0.0


# ── cosine_similarity_normalized ─────────────────────────────────────────────

def test_normalized_similarity_same_as_cosine():
    a = [3.0, 4.0]
    b = [1.0, 0.0]
    direct = cosine_similarity(a, b)
    via_norm = cosine_similarity_normalized(a, b)
    assert direct == pytest.approx(via_norm, abs=1e-9)


# ── top_k_similar ─────────────────────────────────────────────────────────────

def test_top_k_similar_returns_sorted():
    query = [1.0, 0.0]
    candidates = [
        ("a", [1.0, 0.0]),   # sim = 1.0
        ("b", [0.0, 1.0]),   # sim = 0.0
        ("c", [0.7, 0.7]),   # sim ≈ 0.707
    ]
    results = top_k_similar(query, candidates, k=3)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_similar_top_1():
    query = [1.0, 0.0]
    candidates = [
        ("perfect", [1.0, 0.0]),
        ("bad", [0.0, 1.0]),
    ]
    results = top_k_similar(query, candidates, k=1)
    assert len(results) == 1
    assert results[0][0] == "perfect"


def test_top_k_similar_threshold_filters():
    query = [1.0, 0.0]
    candidates = [
        ("above", [0.9, 0.44]),
        ("below", [0.0, 1.0]),  # sim = 0.0
    ]
    results = top_k_similar(query, candidates, k=10, score_threshold=0.5)
    ids = [r[0] for r in results]
    assert "below" not in ids


# ── pairwise_similarity_matrix ────────────────────────────────────────────────

def test_pairwise_matrix_diagonal_is_one():
    vectors = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
    matrix = pairwise_similarity_matrix(vectors)
    for i in range(len(vectors)):
        assert matrix[i][i] == pytest.approx(1.0, abs=1e-9)


def test_pairwise_matrix_symmetric():
    vectors = [[1.0, 0.5], [0.3, 0.8], [0.6, 0.1]]
    matrix = pairwise_similarity_matrix(vectors)
    n = len(vectors)
    for i in range(n):
        for j in range(n):
            assert matrix[i][j] == pytest.approx(matrix[j][i], abs=1e-9)


def test_pairwise_matrix_size():
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    matrix = pairwise_similarity_matrix(vectors)
    assert len(matrix) == 2
    assert all(len(row) == 2 for row in matrix)
