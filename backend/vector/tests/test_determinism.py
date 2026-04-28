"""Tests for backend.vector — determinism guarantees.

Validates that:
 - VectorRecord replay_hash is stable across identical inputs
 - SearchQuery replay_hash is stable across identical inputs
 - Normalization is deterministic
 - Similarity computations are deterministic
 - Clustering is deterministic with fixed seed
"""
from __future__ import annotations

import hashlib
import json
import pytest

from backend.vector.schemas.vector_record import VectorRecord
from backend.vector.schemas.search_query import SearchQuery
from backend.vector.normalization import normalize, l2_norm
from backend.vector.similarity import cosine_similarity
from backend.vector.clustering import cluster_vectors


# ── VectorRecord determinism ──────────────────────────────────────────────────

def test_vector_record_same_inputs_same_replay_hash():
    r1 = VectorRecord(
        collection="signals",
        source_id="sig-001",
        source_type="signal",
        vector=[0.1, 0.2],
        embedding_model="default",
        embedding_provider="auto",
    )
    r2 = VectorRecord(
        collection="signals",
        source_id="sig-001",
        source_type="signal",
        vector=[0.1, 0.2],
        embedding_model="default",
        embedding_provider="auto",
    )
    assert r1.replay_hash == r2.replay_hash


def test_vector_record_different_source_different_hash():
    r1 = VectorRecord(collection="signals", source_id="A", source_type="signal", vector=[1.0])
    r2 = VectorRecord(collection="signals", source_id="B", source_type="signal", vector=[1.0])
    assert r1.replay_hash != r2.replay_hash


def test_vector_record_replay_hash_matches_manual_computation():
    r = VectorRecord(
        collection="signals",
        source_id="manual-test",
        source_type="signal",
        vector=[0.5],
        embedding_model="default",
        embedding_provider="auto",
    )
    canonical = {
        "collection": "signals",
        "source_id": "manual-test",
        "source_type": "signal",
        "embedding_model": "default",
        "embedding_provider": "auto",
    }
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert r.replay_hash == expected


def test_vector_record_custom_replay_hash_preserved():
    custom = "b" * 64
    r = VectorRecord(
        collection="signals",
        source_id="x",
        source_type="signal",
        vector=[0.1],
        replay_hash=custom,
    )
    assert r.replay_hash == custom


def test_vector_record_sequence_id_preserved():
    r = VectorRecord(
        collection="signals",
        source_id="seq-test",
        source_type="signal",
        vector=[0.1],
        sequence_id=42,
    )
    assert r.sequence_id == 42


# ── SearchQuery determinism ───────────────────────────────────────────────────

def test_search_query_replay_hash_stable():
    q1 = SearchQuery(collection="creatives", query_text="winning hooks", top_k=10)
    q2 = SearchQuery(collection="creatives", query_text="winning hooks", top_k=10)
    assert q1.replay_hash == q2.replay_hash


def test_search_query_different_text_different_hash():
    q1 = SearchQuery(collection="signals", query_text="text A")
    q2 = SearchQuery(collection="signals", query_text="text B")
    assert q1.replay_hash != q2.replay_hash


def test_search_query_source_types_order_stable():
    """Source types must be sorted in hash so order does not matter."""
    q1 = SearchQuery(collection="signals", query_text="t", source_types=["a", "b"])
    q2 = SearchQuery(collection="signals", query_text="t", source_types=["b", "a"])
    assert q1.replay_hash == q2.replay_hash


# ── normalization determinism ─────────────────────────────────────────────────

def test_normalize_deterministic():
    v = [3.0, 4.0]
    n1 = normalize(v)
    n2 = normalize(v)
    assert n1 == n2


def test_normalize_unit_length():
    v = [3.0, 4.0]
    nv = normalize(v)
    assert l2_norm(nv) == pytest.approx(1.0, abs=1e-9)


def test_normalize_zero_vector_unchanged():
    z = [0.0, 0.0]
    assert normalize(z) == [0.0, 0.0]


# ── similarity determinism ────────────────────────────────────────────────────

def test_cosine_similarity_deterministic():
    a = [0.3, 0.7, 0.1]
    b = [0.9, 0.2, 0.5]
    s1 = cosine_similarity(a, b)
    s2 = cosine_similarity(a, b)
    assert s1 == s2


def test_cosine_similarity_is_float():
    s = cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert isinstance(s, float)


# ── clustering determinism ────────────────────────────────────────────────────

def test_clustering_deterministic_same_seed():
    vectors = [
        [1.0, 0.0],
        [0.9, 0.1],
        [0.0, 1.0],
        [0.1, 0.9],
    ]
    result1 = cluster_vectors(vectors, k=2, seed=42)
    result2 = cluster_vectors(vectors, k=2, seed=42)
    assert result1["labels"] == result2["labels"]


def test_clustering_returns_correct_n_vectors():
    vectors = [[float(i), float(i + 1)] for i in range(10)]
    result = cluster_vectors(vectors, k=3, seed=0)
    assert result["n_vectors"] == 10


def test_clustering_empty_input():
    result = cluster_vectors([], k=3)
    assert result["n_vectors"] == 0
    assert result["labels"] == []


def test_clustering_k_capped_at_n_vectors():
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    result = cluster_vectors(vectors, k=100)
    assert result["k"] <= 2


# ── round-trip serialisation ──────────────────────────────────────────────────

def test_vector_record_round_trip():
    r = VectorRecord(
        collection="creatives",
        source_id="cr-001",
        source_type="creative",
        vector=[0.1, 0.2, 0.3],
        payload={"product": "widget"},
        sequence_id=7,
    )
    d = r.to_dict()
    r2 = VectorRecord.from_dict(d)
    assert r2.collection == r.collection
    assert r2.source_id == r.source_id
    assert r2.replay_hash == r.replay_hash
    assert r2.sequence_id == r.sequence_id
    assert r2.payload == r.payload
