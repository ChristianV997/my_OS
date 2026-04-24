"""Tests for core/capital_engine.py (CapitalEngineV2)."""
import pytest
from core.capital_engine import CapitalEngineV2, SCALE_ROAS_THRESHOLD, KILL_ROAS_THRESHOLD
from core.pods import Pod


def _pod(roas: float, budget: float = 100.0, spend: float = 50.0) -> Pod:
    pod = Pod("widget", "US", "tiktok", budget=budget)
    pod.metrics = {"roas": roas, "spend": spend, "revenue": roas * spend}
    return pod


# ------------------------------------------------------------------
# evaluate()
# ------------------------------------------------------------------

def test_evaluate_scale():
    engine = CapitalEngineV2()
    pod = _pod(roas=SCALE_ROAS_THRESHOLD + 0.5)
    assert engine.evaluate(pod) == "scale"


def test_evaluate_kill_tiny_budget():
    engine = CapitalEngineV2()
    pod = _pod(roas=KILL_ROAS_THRESHOLD - 0.1, budget=3.0)
    assert engine.evaluate(pod) == "kill"


def test_evaluate_reduce():
    engine = CapitalEngineV2()
    pod = _pod(roas=KILL_ROAS_THRESHOLD - 0.1, budget=50.0)
    assert engine.evaluate(pod) == "reduce"


def test_evaluate_hold():
    engine = CapitalEngineV2()
    pod = _pod(roas=1.5)  # between kill(1) and scale(2)
    assert engine.evaluate(pod) == "hold"


# ------------------------------------------------------------------
# apply()
# ------------------------------------------------------------------

def test_apply_scale_increases_budget():
    engine = CapitalEngineV2()
    pod = _pod(roas=3.0, budget=100.0)
    old_budget = pod.budget
    decision = engine.apply(pod)
    assert decision == "scale"
    assert pod.budget > old_budget
    assert pod.status == "scaling"


def test_apply_scale_capped_at_daily_cap():
    engine = CapitalEngineV2(daily_cap=110.0)
    pod = _pod(roas=10.0, budget=100.0)
    engine.apply(pod)
    assert pod.budget <= 110.0


def test_apply_scale_min_increase():
    engine = CapitalEngineV2(min_scale_factor=0.20, max_scale_factor=0.50)
    pod = _pod(roas=SCALE_ROAS_THRESHOLD + 0.01, budget=100.0)
    engine.apply(pod)
    # Should be at least 20% above original
    assert pod.budget >= 120.0 - 0.01  # allow tiny float error


def test_apply_reduce_halves_budget():
    engine = CapitalEngineV2()
    pod = _pod(roas=0.5, budget=100.0)
    engine.apply(pod)
    assert pod.budget == pytest.approx(50.0, abs=0.01)


def test_apply_reduce_kills_when_budget_near_zero():
    engine = CapitalEngineV2()
    pod = _pod(roas=0.5, budget=1.5)
    engine.apply(pod)
    assert pod.status == "killed"
    assert pod.budget == 0.0


def test_apply_kill():
    engine = CapitalEngineV2()
    pod = _pod(roas=0.5, budget=3.0)
    decision = engine.apply(pod)
    assert decision == "kill"
    assert pod.status == "killed"
    assert pod.budget == 0.0


def test_apply_hold_no_change():
    engine = CapitalEngineV2()
    pod = _pod(roas=1.5, budget=100.0)
    original_budget = pod.budget
    decision = engine.apply(pod)
    assert decision == "hold"
    assert pod.budget == original_budget
    assert pod.status == "testing"


# ------------------------------------------------------------------
# spend tracking
# ------------------------------------------------------------------

def test_record_spend_accumulates():
    engine = CapitalEngineV2()
    engine.record_spend("pod_1", 50.0)
    engine.record_spend("pod_1", 30.0)
    assert engine.pod_spend("pod_1") == 80.0


def test_reset_spend():
    engine = CapitalEngineV2()
    engine.record_spend("pod_1", 100.0)
    engine.reset_spend("pod_1")
    assert engine.pod_spend("pod_1") == 0.0


def test_pod_spend_unknown_returns_zero():
    engine = CapitalEngineV2()
    assert engine.pod_spend("no-such-pod") == 0.0


# ------------------------------------------------------------------
# daily cap enforcement
# ------------------------------------------------------------------

def test_enforce_daily_cap_kills_overspent_pod():
    engine = CapitalEngineV2(daily_cap=100.0)
    pod = _pod(roas=3.0, budget=50.0, spend=100.0)
    engine.record_spend(pod.id, 100.0)
    killed = engine.enforce_daily_cap(pod)
    assert killed is True
    assert pod.status == "killed"


def test_enforce_daily_cap_no_action_under_cap():
    engine = CapitalEngineV2(daily_cap=500.0)
    pod = _pod(roas=3.0, budget=50.0, spend=50.0)
    engine.record_spend(pod.id, 50.0)
    killed = engine.enforce_daily_cap(pod)
    assert killed is False
    assert pod.status != "killed"


# ------------------------------------------------------------------
# budget allocation
# ------------------------------------------------------------------

def test_allocate_budget_even_split():
    engine = CapitalEngineV2()
    pods = [_pod(roas=2.5), _pod(roas=2.5)]
    alloc = engine.allocate_budget(pods, 1000.0)
    assert len(alloc) == 2
    for v in alloc.values():
        assert abs(v - 500.0) < 1.0


def test_allocate_budget_skips_killed():
    engine = CapitalEngineV2(daily_cap=2000.0)  # cap above total_budget so it doesn't interfere
    pod_a = _pod(roas=3.0)
    pod_b = _pod(roas=1.0)
    pod_b.status = "killed"
    alloc = engine.allocate_budget([pod_a, pod_b], 1000.0)
    assert pod_b.id not in alloc
    assert abs(alloc[pod_a.id] - 1000.0) < 1.0


def test_allocate_budget_all_killed():
    engine = CapitalEngineV2()
    pod = _pod(roas=0.0)
    pod.status = "killed"
    assert engine.allocate_budget([pod], 1000.0) == {}


def test_allocate_budget_respects_daily_cap():
    engine = CapitalEngineV2(daily_cap=200.0)
    pods = [_pod(roas=3.0) for _ in range(3)]
    alloc = engine.allocate_budget(pods, 1000.0)
    for v in alloc.values():
        assert v <= 200.0 + 0.01


def test_allocate_budget_respects_max_concurrent():
    engine = CapitalEngineV2(max_concurrent_pods=2)
    pods = [_pod(roas=float(i)) for i in range(5)]
    alloc = engine.allocate_budget(pods, 1000.0)
    assert len(alloc) <= 2
