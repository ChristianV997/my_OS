"""Tests for deterministic vector IDs and idempotent upserts."""
import pytest

from backend.vector.normalization  import deterministic_id, normalize, stamp_lineage
from backend.vector.indexing       import make_record, hook_record
from backend.vector.schemas        import VectorRecord
from backend.inference.providers.mock import MockProvider
from backend.inference.models.embedding_request import EmbeddingRequest


def test_deterministic_id_same_inputs():
    a = deterministic_id("hook", "This changed everything")
    b = deterministic_id("hook", "This changed everything")
    assert a == b


def test_deterministic_id_different_inputs():
    a = deterministic_id("hook", "hook A")
    b = deterministic_id("hook", "hook B")
    assert a != b


def test_deterministic_id_different_sources():
    a = deterministic_id("hook", "same key")
    b = deterministic_id("product", "same key")
    assert a != b


def test_normalize_unit_vector():
    import math
    v    = [3.0, 4.0]
    norm = normalize(v)
    mag  = math.sqrt(sum(x * x for x in norm))
    assert abs(mag - 1.0) < 1e-9


def test_normalize_zero_vector():
    v = [0.0, 0.0, 0.0]
    assert normalize(v) == [0.0, 0.0, 0.0]


def test_stamp_lineage_adds_source():
    payload = {"hook": "test"}
    stamped = stamp_lineage(payload, source="test_module")
    assert stamped["_source"] == "test_module"
    assert "_ts" in stamped


def test_stamp_lineage_no_mutation():
    payload = {"key": "value"}
    stamp_lineage(payload, source="x")
    assert "_source" not in payload


def test_make_record_deterministic_id():
    mock = MockProvider()
    req  = EmbeddingRequest(texts=["hook text"])
    vecs = mock.embed(req)
    r1 = make_record(source="hook", key="hook text", collection="hooks",
                     vector=vecs[0], payload={})
    r2 = make_record(source="hook", key="hook text", collection="hooks",
                     vector=vecs[0], payload={})
    assert r1.record_id == r2.record_id


def test_hook_record_is_vector_record():
    mock = MockProvider()
    req  = EmbeddingRequest(texts=["some hook"])
    vecs = mock.embed(req)
    rec  = hook_record("some hook", vecs[0])
    assert isinstance(rec, VectorRecord)
    assert rec.collection == "hooks"
    assert rec.source     == "hook"


def test_upsert_idempotent(fresh_store):
    mock = MockProvider()
    req  = EmbeddingRequest(texts=["idempotent hook"])
    vecs = mock.embed(req)
    rec  = hook_record("idempotent hook", vecs[0])
    fresh_store.upsert([rec])
    fresh_store.upsert([rec])
    assert fresh_store.count("hooks") == 1


def test_mock_embedding_deterministic():
    mock = MockProvider()
    t    = "deterministic vector test"
    r1   = EmbeddingRequest(texts=[t])
    r2   = EmbeddingRequest(texts=[t])
    assert mock.embed(r1) == mock.embed(r2)
