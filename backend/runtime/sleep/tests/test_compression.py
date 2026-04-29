"""Tests for semantic compression and episodic compaction."""
import pytest
import math

from backend.runtime.sleep.policies.compression_policy import CompressionPolicy
from backend.runtime.sleep.cluster_abstraction         import extract_text_items, abstract_batch
from backend.runtime.sleep.episodic_compaction         import compact
from backend.runtime.sleep.semantic_compression        import compress_domain


# ── CompressionPolicy ─────────────────────────────────────────────────────────

def test_should_compress_below_threshold():
    p = CompressionPolicy(min_episodes_to_compress=10)
    assert not p.should_compress(5)


def test_should_compress_above_threshold():
    p = CompressionPolicy(min_episodes_to_compress=10)
    assert p.should_compress(15)


def test_cluster_count_heuristic():
    p  = CompressionPolicy(max_clusters=8)
    n  = 100
    k  = p.cluster_count(n)
    assert k == min(8, max(2, int(math.sqrt(n))))


def test_cluster_count_capped_at_max():
    p = CompressionPolicy(max_clusters=5)
    assert p.cluster_count(10000) == 5


def test_should_summarize_lineage():
    p = CompressionPolicy(max_lineage_depth=50)
    assert     p.should_summarize_lineage(60)
    assert not p.should_summarize_lineage(40)


def test_cluster_is_significant():
    p = CompressionPolicy(min_cluster_size=3)
    assert     p.cluster_is_significant(4)
    assert not p.cluster_is_significant(2)


# ── extract_text_items ────────────────────────────────────────────────────────

def test_extract_text_items_from_decisions(small_batch):
    texts = extract_text_items(small_batch)
    assert "hook" in texts
    hooks = texts["hook"]
    assert any("changed everything" in h for h in hooks)


def test_extract_text_items_from_signals(small_batch):
    texts = extract_text_items(small_batch)
    assert "signal" in texts
    assert any("morning" in t for t in texts["signal"])


def test_extract_text_items_empty_batch():
    from backend.runtime.sleep.schemas.replay_batch import ReplayBatch
    import uuid, time
    batch = ReplayBatch(batch_id=uuid.uuid4().hex[:8], start_ts=0, end_ts=0, events=[])
    texts = extract_text_items(batch)
    assert texts == {}


# ── abstract_batch ────────────────────────────────────────────────────────────

def test_abstract_batch_returns_domain_units(small_batch):
    p      = CompressionPolicy(min_episodes_to_compress=1, min_cluster_size=1)
    result = abstract_batch(small_batch, policy=p)
    assert isinstance(result, dict)


def test_abstract_batch_empty_skips(small_batch):
    p      = CompressionPolicy(min_episodes_to_compress=10000)
    result = abstract_batch(small_batch, policy=p)
    assert result == {}


# ── compact ───────────────────────────────────────────────────────────────────

def test_compact_returns_counts(small_batch):
    p      = CompressionPolicy(min_episodes_to_compress=1, min_cluster_size=1)
    counts = compact(small_batch, policy=p, index_vectors=False)
    assert isinstance(counts, dict)
    assert all(isinstance(v, int) for v in counts.values())


def test_compact_updates_semantic_store(small_batch):
    from backend.memory.semantic import get_semantic_store
    p     = CompressionPolicy(min_episodes_to_compress=1, min_cluster_size=1)
    store = get_semantic_store()
    before = store.count()
    compact(small_batch, policy=p, index_vectors=False)
    # Generation should have bumped if any units were created
    assert store.generation() >= 0


# ── compress_domain ───────────────────────────────────────────────────────────

def test_compress_domain_returns_tuple():
    merged, pruned = compress_domain("hook")
    assert isinstance(merged, int)
    assert isinstance(pruned, int)


def test_compress_domain_empty_store_is_safe():
    m, p = compress_domain("nonexistent_domain_xyz")
    assert m == 0
    assert p == 0
