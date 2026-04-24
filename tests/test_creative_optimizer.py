"""Tests for agents/creative_optimizer.py"""
import pytest
from agents.creative_optimizer import CreativeOptimizer


@pytest.fixture()
def optimizer():
    return CreativeOptimizer(ctr_threshold=0.015, cvr_threshold=0.01)


def test_record_and_rank_by_ctr(optimizer):
    optimizer.record("c1", {"ctr": 0.03, "cvr": 0.02})
    optimizer.record("c2", {"ctr": 0.005, "cvr": 0.001})
    ranked = optimizer.rank_by_ctr()
    assert ranked[0][0] == "c1"
    assert ranked[1][0] == "c2"


def test_rank_by_cvr(optimizer):
    optimizer.record("c1", {"ctr": 0.02, "cvr": 0.05})
    optimizer.record("c2", {"ctr": 0.03, "cvr": 0.01})
    ranked = optimizer.rank_by_cvr()
    assert ranked[0][0] == "c1"


def test_winners(optimizer):
    optimizer.record("c1", {"ctr": 0.03, "cvr": 0.02})
    optimizer.record("c2", {"ctr": 0.005, "cvr": 0.001})
    winners = optimizer.winners()
    assert len(winners) == 1
    assert winners[0][0] == "c1"


def test_losers(optimizer):
    optimizer.record("c1", {"ctr": 0.03, "cvr": 0.02})
    optimizer.record("c2", {"ctr": 0.005, "cvr": 0.001})
    losers = optimizer.losers()
    assert len(losers) == 1
    assert losers[0][0] == "c2"


def test_discard_losers(optimizer):
    optimizer.record("c1", {"ctr": 0.03, "cvr": 0.02})
    optimizer.record("c2", {"ctr": 0.005, "cvr": 0.001})
    discarded = optimizer.discard_losers()
    assert "c2" in discarded
    assert "c1" not in discarded
    # c2 should be gone from metrics
    assert "c2" not in dict(optimizer.rank_by_ctr())


def test_mutate_adds_version(optimizer):
    creative = {"id": "c1", "headline": "Buy now", "body": "Great product", "cta": "Shop Now"}
    mutated = optimizer.mutate(creative)
    assert "(v2)" in mutated["headline"]
    # original is unchanged
    assert "v2" not in creative["headline"]


def test_mutate_increments_version(optimizer):
    creative = {"id": "c1", "headline": "Buy now (v2)"}
    mutated = optimizer.mutate(creative)
    assert "(v3)" in mutated["headline"]


def test_generate_variants_empty_when_no_winners(optimizer):
    optimizer.record("c1", {"ctr": 0.001, "cvr": 0.001})
    variants = optimizer.generate_variants(count=2)
    assert variants == []


def test_generate_variants_from_winners(optimizer):
    creative = {"id": "c1", "headline": "Win now", "body": "text", "cta": "Buy"}
    optimizer.register(creative)
    optimizer.record("c1", {"ctr": 0.03, "cvr": 0.02})
    variants = optimizer.generate_variants(count=2)
    assert len(variants) == 2
    for v in variants:
        assert "(v2)" in v["headline"]


def test_register_and_get_variant(optimizer):
    creative = {"id": "cx", "headline": "Test headline"}
    optimizer.register(creative)
    optimizer.record("cx", {"ctr": 0.05, "cvr": 0.03})
    variants = optimizer.generate_variants(count=1)
    assert len(variants) == 1


def test_no_metrics_empty_rank(optimizer):
    assert optimizer.rank_by_ctr() == []
    assert optimizer.winners() == []
    assert optimizer.losers() == []
