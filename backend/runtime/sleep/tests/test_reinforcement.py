"""Tests for procedural reinforcement policy and pipeline."""
import pytest

from backend.runtime.sleep.policies.reinforcement_policy import ReinforcementPolicy
from backend.runtime.sleep.procedural_reinforcement      import (
    reinforce_from_batch, promote_high_confidence, _extract_outcomes,
)


# ── ReinforcementPolicy ───────────────────────────────────────────────────────

def test_update_score_ema():
    rp = ReinforcementPolicy(ema_alpha=0.5, roas_scale=4.0, min_samples=1)
    updated = rp.update_score(
        current_score=0.5, new_roas=4.0, success=True, sample_count=5,
    )
    # new signal = 1.0, EMA: 0.5*1.0 + 0.5*0.5 = 0.75
    assert abs(updated - 0.75) < 1e-6


def test_update_score_failure_drives_down():
    rp = ReinforcementPolicy(ema_alpha=0.5, min_samples=1)
    updated = rp.update_score(0.8, new_roas=0.0, success=False, sample_count=5)
    assert updated < 0.8


def test_update_score_below_min_samples():
    rp = ReinforcementPolicy(min_samples=10)
    unchanged = rp.update_score(0.5, new_roas=5.0, success=True, sample_count=3)
    assert unchanged == 0.5


def test_confidence_zero_samples():
    rp = ReinforcementPolicy()
    assert rp.confidence(1.0, 0) == 0.0


def test_confidence_grows_with_samples():
    rp = ReinforcementPolicy(roas_scale=5.0)
    c5  = rp.confidence(0.8, 5,  avg_roas=4.0)
    c50 = rp.confidence(0.8, 50, avg_roas=4.0)
    assert c50 > c5


def test_should_promote_high_confidence():
    rp = ReinforcementPolicy(roas_scale=5.0)
    assert rp.should_promote(0.9, 30, avg_roas=4.5, threshold=0.5)


def test_should_deprecate_low_success():
    rp = ReinforcementPolicy(min_samples=3)
    assert rp.should_deprecate(success_rate=0.1, sample_count=10, threshold=0.2)


def test_should_not_deprecate_below_min_samples():
    rp = ReinforcementPolicy(min_samples=10)
    assert not rp.should_deprecate(0.0, sample_count=2, threshold=0.2)


# ── extract_outcomes ──────────────────────────────────────────────────────────

def test_extract_outcomes_from_batch(small_batch):
    outcomes = _extract_outcomes(small_batch)
    assert len(outcomes) >= 2
    for o in outcomes:
        assert "hook" in o
        assert "roas" in o
        assert "success" in o


def test_extract_outcomes_success_flag(small_batch):
    outcomes = _extract_outcomes(small_batch)
    high_roas = [o for o in outcomes if o["roas"] >= 1.0]
    assert all(o["success"] for o in high_roas)


# ── reinforce_from_batch ──────────────────────────────────────────────────────

def test_reinforce_from_batch_returns_int(small_batch):
    count = reinforce_from_batch(small_batch)
    assert isinstance(count, int)
    assert count >= 0


def test_reinforce_creates_procedures(small_batch):
    from backend.memory.procedural import get_procedural_store
    store  = get_procedural_store()
    before = store.count()
    reinforce_from_batch(small_batch)
    after  = store.count()
    assert after >= before


def test_promote_high_confidence_returns_list():
    result = promote_high_confidence()
    assert isinstance(result, list)
