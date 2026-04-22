import numpy as np
from backend.decision.confidence import ConfidenceEngine, apply_confidence


def test_confidence_decreases_with_gap():
    engine = ConfidenceEngine()

    gaps = np.linspace(0.1, 2.0, 30)
    errors = np.zeros_like(gaps)

    confidences = []

    for g, e in zip(gaps, errors):
        c = engine.compute(g, e)
        confidences.append(c)

    # Ensure confidence decreases as gap increases
    for i in range(1, len(confidences)):
        if confidences[i] > confidences[i - 1] + 0.05:
            print("\n--- DEBUG CONFIDENCE TRACE ---")
            print("GAPS:", [round(x, 3) for x in gaps])
            print("CONFIDENCE:", [round(x, 3) for x in confidences])
            raise AssertionError("Confidence not decreasing with increasing gap")


def test_confidence_stability():
    engine = ConfidenceEngine()

    gap = 0.5
    error = 0.2

    confidences = [engine.compute(gap, error) for _ in range(50)]

    variance = np.var(confidences)

    if variance > 0.01:
        print("\n--- DEBUG CONFIDENCE STABILITY ---")
        print("CONFIDENCE SERIES:", [round(x, 3) for x in confidences])
        raise AssertionError("Confidence unstable under constant conditions")


def test_apply_confidence_controls_exploration_and_scaling():
    low = apply_confidence({"score": 10.0}, 0.3)
    high = apply_confidence({"score": 10.0}, 0.9)

    assert low["exploration_boost"] > high["exploration_boost"]
    assert low["scale_down"] is True
    assert high["scale_down"] is False


def test_apply_confidence_transition_temporarily_boosts_exploration_and_dampens_confidence():
    baseline = apply_confidence({"score": 10.0}, 0.6, transition=False, cooldown=0)
    shifted = apply_confidence({"score": 10.0}, 0.6, transition=True, cooldown=5)

    assert shifted["confidence"] < baseline["confidence"]
    assert shifted["exploration_boost"] > baseline["exploration_boost"]
    assert shifted["transition_adjustment"]["occurred"] is True


def test_apply_confidence_transition_adds_exploration_even_when_baseline_zero():
    baseline = apply_confidence({"score": 10.0}, 0.9, transition=False, cooldown=0)
    shifted = apply_confidence({"score": 10.0}, 0.9, transition=True, cooldown=0)
    assert baseline["exploration_boost"] == 0.0
    assert shifted["exploration_boost"] > 0.0
