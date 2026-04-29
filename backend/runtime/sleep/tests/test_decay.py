"""Tests for memory decay and retention policies."""
import time
import pytest

from backend.runtime.sleep.policies.decay_policy      import DecayPolicy
from backend.runtime.sleep.policies.retention_policy  import RetentionPolicy, RetentionDecision
from backend.runtime.sleep.memory_decay               import run_decay_pass


# ── DecayPolicy ───────────────────────────────────────────────────────────────

def test_decay_score_fresh_item_high():
    dp    = DecayPolicy(base_lambda=0.01)
    score = dp.decay_score(base_score=1.0, ts=time.time(), domain="hook")
    assert score > 0.8


def test_decay_score_old_item_lower():
    dp   = DecayPolicy(base_lambda=0.1)
    old  = dp.decay_score(1.0, ts=time.time() - 10000, domain="hook")
    fresh = dp.decay_score(1.0, ts=time.time(),        domain="hook")
    assert old < fresh


def test_decay_roas_resists_decay():
    dp = DecayPolicy(base_lambda=0.5)
    low_roas  = dp.decay_score(0.3, ts=time.time() - 7200, domain="hook", avg_roas=0.0)
    high_roas = dp.decay_score(0.3, ts=time.time() - 7200, domain="hook", avg_roas=8.0)
    assert high_roas > low_roas


def test_should_prune_zero_score():
    dp = DecayPolicy(prune_threshold=0.1)
    assert dp.should_prune(0.0, ts=time.time() - 9999, domain="signal")


def test_should_not_prune_fresh_high_score():
    dp = DecayPolicy(prune_threshold=0.05)
    assert not dp.should_prune(1.0, ts=time.time(), domain="hook")


def test_rank_by_retention_sorted():
    dp = DecayPolicy()
    items = [
        {"score": 0.2, "ts": time.time() - 5000, "domain": "hook"},
        {"score": 0.9, "ts": time.time(),         "domain": "hook"},
        {"score": 0.5, "ts": time.time() - 1000,  "domain": "hook"},
    ]
    ranked = dp.rank_by_retention(items)
    scores = [dp.decay_score(i["score"], i["ts"], i["domain"]) for i in ranked]
    assert scores == sorted(scores, reverse=True)


# ── RetentionPolicy ───────────────────────────────────────────────────────────

def test_retention_keep_high_score():
    rp = RetentionPolicy(keep_threshold=0.6)
    decision = rp.decide(retention_score=0.9, ts=time.time())
    assert decision == RetentionDecision.KEEP


def test_retention_compact_medium_score():
    rp = RetentionPolicy(keep_threshold=0.6, compact_threshold=0.2)
    decision = rp.decide(retention_score=0.4, ts=time.time())
    assert decision == RetentionDecision.COMPACT


def test_retention_discard_low_score():
    rp = RetentionPolicy(compact_threshold=0.2)
    decision = rp.decide(retention_score=0.05, ts=time.time())
    assert decision == RetentionDecision.DISCARD


def test_retention_discard_old_low_score():
    rp = RetentionPolicy(max_age_hours=1.0, compact_threshold=0.2)
    ancient = time.time() - 7200   # 2 hours old
    decision = rp.decide(retention_score=0.1, ts=ancient)
    assert decision == RetentionDecision.DISCARD


def test_retention_forced_keep():
    rp = RetentionPolicy()
    decision = rp.decide(retention_score=0.0, ts=time.time() - 9999, forced_keep=True)
    assert decision == RetentionDecision.KEEP


def test_classify_batch():
    rp    = RetentionPolicy(keep_threshold=0.7, compact_threshold=0.3)
    items = [
        {"retention_score": 0.9, "ts": time.time()},
        {"retention_score": 0.5, "ts": time.time()},
        {"retention_score": 0.1, "ts": time.time()},
    ]
    bins = rp.classify_batch(items)
    assert len(bins[RetentionDecision.KEEP])    == 1
    assert len(bins[RetentionDecision.COMPACT]) == 1
    assert len(bins[RetentionDecision.DISCARD]) == 1


# ── run_decay_pass ────────────────────────────────────────────────────────────

def test_run_decay_pass_returns_dict():
    result = run_decay_pass()
    assert isinstance(result, dict)
    assert "semantic_pruned"    in result
    assert "episodic_compacted" in result
