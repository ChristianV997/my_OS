import random

from backend.decision.scoring import causal_score
from backend.decision.confidence import confidence_engine
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight
from backend.learning.calibration import calibration_model
from backend.simulation.reality_gap import reality_gap_engine
from backend.core.state import ensure_state_shape
from agents.world_model import world_model


def _interval_confidence(preds: dict) -> float:
    widths = [preds.get(f"width_{h}", 0.6) for h in ("6h", "12h", "24h")]
    mean_width = sum(widths) / len(widths)
    return 1.0 / (1.0 + mean_width)


def decide(state):
    state = ensure_state_shape(state)
    world_model.train(state.event_log)

    history = [r.get("roas", 0) for r in state.event_log.rows[-10:]]
    vel = roas_velocity(history)
    acc = roas_acceleration(history)

    # reality-gap + calibration composite confidence (smoothed EMA)
    gap_summary = reality_gap_engine.summary()
    cal_stats = calibration_model.stats()
    system_conf = confidence_engine.compute(
        reality_gap=gap_summary.get("reality_gap"),
        calibration_error=cal_stats.get("bias"),
    )

    decisions = []

    for _ in range(5):
        action = {"variant": random.randint(1, 5)}
        preds = world_model.predict(action)

        weighted_pred = (
            0.5 * preds["roas_6h"] +
            0.3 * preds["roas_12h"] +
            0.2 * preds["roas_24h"]
        )

        corrected_pred = calibration_model.adjust_prediction(weighted_pred)

        c_score = causal_score(action, state.graph)
        velocity_bonus = vel + acc
        bandit_w = bandit_weight(action, state.graph)

        # three-factor confidence: calibration × interval narrowness × system health
        calib_conf = calibration_model.confidence_weight()
        interval_conf = _interval_confidence(preds)
        confidence = calib_conf * interval_conf * system_conf

        score = (corrected_pred + c_score + velocity_bonus + bandit_w) * confidence

        decisions.append({
            "action":        action,
            "score":         score,
            "pred":          corrected_pred,
            "pred_lo":       round(0.5 * preds["lo_6h"] + 0.3 * preds["lo_12h"] + 0.2 * preds["lo_24h"], 4),
            "pred_hi":       round(0.5 * preds["hi_6h"] + 0.3 * preds["hi_12h"] + 0.2 * preds["hi_24h"], 4),
            "pred_width":    round(0.5 * preds["width_6h"] + 0.3 * preds["width_12h"] + 0.2 * preds["width_24h"], 4),
            "interval_conf": round(interval_conf, 4),
            "system_conf":   round(system_conf, 4),
        })

    decisions.sort(key=lambda x: x["score"], reverse=True)
    return decisions
