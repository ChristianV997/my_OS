import math

TRANSITION_CONFIDENCE_DAMPING = 0.85
TRANSITION_EXPLORATION_MULTIPLIER = 1.3
TRANSITION_COOLDOWN_EXPLORATION_MULTIPLIER = 1.1


class ConfidenceEngine:
    def __init__(self):
        self.last_confidence = 1.0

    def compute(self, reality_gap: float | None, calibration_error: float | None):
        """
        Combine reality gap + calibration error into confidence score [0,1]
        Lower gap + lower error → higher confidence
        """
        if reality_gap is None and calibration_error is None:
            return 1.0

        gap = reality_gap if reality_gap is not None else 0.0
        err = calibration_error if calibration_error is not None else 0.0

        # normalize using soft exponential decay
        gap_term = math.exp(-gap)
        err_term = math.exp(-abs(err))

        confidence = 0.6 * gap_term + 0.4 * err_term

        # smooth to avoid oscillations
        confidence = 0.8 * self.last_confidence + 0.2 * confidence
        self.last_confidence = confidence

        return max(0.05, min(1.0, confidence))


confidence_engine = ConfidenceEngine()


def apply_confidence(decision: dict, confidence: float, transition: bool = False, cooldown: int = 0):
    """Modify decision score and exploration based on confidence"""
    effective_confidence = confidence * TRANSITION_CONFIDENCE_DAMPING if transition else confidence

    # scale score
    decision["score"] *= effective_confidence

    # attach confidence for logging
    decision["confidence"] = effective_confidence

    # adaptive behavior
    if effective_confidence < 0.4:
        decision["exploration_boost"] = 0.3
        decision["scale_down"] = True
    elif effective_confidence < 0.7:
        decision["exploration_boost"] = 0.1
        decision["scale_down"] = False
    else:
        decision["exploration_boost"] = 0.0
        decision["scale_down"] = False

    if transition:
        decision["exploration_boost"] *= TRANSITION_EXPLORATION_MULTIPLIER
    if cooldown > 0:
        decision["exploration_boost"] *= TRANSITION_COOLDOWN_EXPLORATION_MULTIPLIER

    decision["exploration_boost"] = min(1.0, decision["exploration_boost"])
    decision["transition_adjustment"] = {
        "occurred": transition,
        "cooldown": max(0, cooldown),
    }

    return decision
