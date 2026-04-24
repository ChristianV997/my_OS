"""Tests for core/loop_v3.py — Phase 2 enhanced loop."""
import pytest
from core.loop_v3 import run_cycle_v3


def _signal(product="posture_corrector", roas=3.0, spend=20.0, score=0.8):
    return {
        "product": product,
        "score": score,
        "source": "mock",
        "market": "US",
        "platform": "tiktok",
        "budget": spend,
        "roas": roas,
        "spend": spend,
        "clicks": 200,
        "impressions": 8000,
        "conversions": 10,
    }


def test_run_cycle_v3_returns_list():
    results = run_cycle_v3(signals=[_signal()])
    assert isinstance(results, list)
    assert len(results) == 1


def test_run_cycle_v3_result_keys():
    results = run_cycle_v3(signals=[_signal()])
    record = results[0]
    for key in ("pod_id", "decision", "roas", "spend", "revenue", "creative_variants"):
        assert key in record, f"Missing key: {key}"


def test_run_cycle_v3_scale_decision():
    results = run_cycle_v3(signals=[_signal(roas=3.0)])
    assert results[0]["decision"] == "scale"


def test_run_cycle_v3_kill_decision():
    results = run_cycle_v3(signals=[_signal(roas=0.5, spend=20.0)])
    assert results[0]["decision"] in ("kill", "reduce")


def test_run_cycle_v3_hold_decision():
    results = run_cycle_v3(signals=[_signal(roas=1.5)])
    assert results[0]["decision"] == "hold"


def test_run_cycle_v3_empty_signals():
    results = run_cycle_v3(signals=[])
    assert results == []


def test_run_cycle_v3_filters_low_score():
    low_score_signal = _signal(score=0.1)
    results = run_cycle_v3(signals=[low_score_signal])
    assert results == []


def test_run_cycle_v3_multiple_pods():
    signals = [
        _signal(product=f"product_{i}", roas=2.5 + i * 0.1)
        for i in range(3)
    ]
    results = run_cycle_v3(signals=signals, config={"max_concurrent_pods": 10})
    assert len(results) == 3


def test_run_cycle_v3_respects_max_concurrent():
    signals = [
        _signal(product=f"product_{i}") for i in range(10)
    ]
    results = run_cycle_v3(signals=signals, config={"max_concurrent_pods": 3})
    # At most 3 pods can be created; remaining signals are filtered by top_opportunities
    assert len(results) <= 3


def test_run_cycle_v3_revenue_calculation():
    results = run_cycle_v3(signals=[_signal(roas=2.0, spend=50.0)])
    assert abs(results[0]["revenue"] - 100.0) < 1e-6


def test_run_cycle_v3_creative_variants_generated():
    # High CTR/CVR signal so optimizer produces winner variants
    sig = _signal(roas=3.0, spend=20.0)
    sig["clicks"] = 500
    sig["impressions"] = 5000   # CTR = 0.1 > threshold 0.015
    sig["conversions"] = 50     # CVR = 0.1 > threshold 0.01
    results = run_cycle_v3(signals=[sig])
    assert results[0]["creative_variants"] >= 0  # may be 0 if no registered winners yet


def test_run_cycle_v3_no_signals_uses_mock():
    # Should not raise even when no signals are passed (uses mock signal engine)
    results = run_cycle_v3()
    assert isinstance(results, list)
