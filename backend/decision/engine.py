from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight, recommend_action
from backend.learning.calibration import calibration_model
from backend.learning.campaign_learning import campaign_learning
from backend.decision.confidence import confidence_engine, apply_confidence
from backend.agents.campaign_budget import campaign_budget_allocator
from backend.agents.structural_evolution import structural_engine
from backend.agents.strategies import strategies
from backend.agents.allocator import allocator
from backend.core.state import ensure_state_shape
from agents.world_model import world_model

import random

CAMPAIGN_WEIGHT = 0.5
BUDGET_WEIGHT = 0.3
SCALE_DOWN_FACTOR = 0.7
DEFAULT_ROAS_PREDICTION = 1.0
DEFAULT_ROAS_PREDICTIONS = {
    "roas_6h": DEFAULT_ROAS_PREDICTION,
    "roas_12h": DEFAULT_ROAS_PREDICTION,
    "roas_24h": DEFAULT_ROAS_PREDICTION,
}


REGIME_CODE = {
    "unknown": 0.0,
    "neutral": 0.25,
    "stable": 0.5,
    "growth": 0.75,
    "decay": -0.75,
    "volatile": -0.5,
}


def _safe_rows(state):
    event_log = getattr(state, "event_log", None)
    return getattr(event_log, "rows", [])


def _safe_graph(state):
    graph = getattr(state, "graph", None)
    return graph if graph is not None else type("GraphStub", (), {"edges": {}})()


def _context_features(state, action=None):
    action = action or {}
    rows = _safe_rows(state)
    history = [float(r.get("roas", 0)) for r in rows[-10:]]
    vel = roas_velocity(history)
    acc = roas_acceleration(history)
    recent_roas = sum(history) / len(history) if history else 0.0
    causal_insights = getattr(state, "causal_insights", {}) or {}
    best_effect = causal_insights.get("best_roas_effect", 0.0)
    return {
        "regime_code": REGIME_CODE.get(getattr(state, "regime", "unknown"), 0.0),
        "detected_regime_code": REGIME_CODE.get(getattr(state, "detected_regime", "unknown"), 0.0),
        "capital": float(getattr(state, "capital", 0.0)),
        "recent_roas": float(recent_roas),
        "roas_velocity": float(vel),
        "roas_acceleration": float(acc),
        "causal_roas_effect": float(best_effect),
        "cycle": float(getattr(state, "total_cycles", getattr(state, "step", 0))),
        "variant": float(action.get("variant", 0)),
        "intensity": float(action.get("intensity", 0)),
    }


def decide(state):
    state = ensure_state_shape(state)

    if not structural_engine.population:
        structural_engine.initialize()

    graph = _safe_graph(state)
    rows = _safe_rows(state)

    if hasattr(state, "event_log") and state.event_log is not None:
        world_model.train(state.event_log)

    history = [r.get("roas", 0) for r in rows[-10:]]
    vel = roas_velocity(history)
    acc = roas_acceleration(history)

    decisions=[]

    total_budget = 10
    calibration_error = abs(calibration_model.stats().get("bias", 0.0))
    reality_gap = getattr(state, "last_reality_gap", None)
    confidence = confidence_engine.compute(reality_gap, calibration_error)
    confidence_template = apply_confidence({"score": 1.0}, confidence)

    if confidence >= 0.7:
        structure = max(
            structural_engine.population,
            key=lambda s: s.get("memory", {}).get("avg_perf", 0.0)
        )
    else:
        structure = random.choice(structural_engine.population)

    if confidence_template.get("scale_down"):
        total_budget = max(5, int(total_budget * SCALE_DOWN_FACTOR))

    strategy_pool = getattr(state, "strategies", None) or strategies

    for name, strat in strategy_pool.items():

        n_actions = allocator.allocate(
            name,
            total_budget,
            confidence=confidence,
            exploration_boost=confidence_template.get("exploration_boost", 0.0),
        )
        if n_actions <= 0:
            continue

        proposals = strat.propose(state)
        proposals = proposals[:n_actions]

        for action in proposals:
            if rows:
                preds = world_model.predict({"variant": action.get("variant", 0)})
            else:
                preds = DEFAULT_ROAS_PREDICTIONS

            weighted_pred = (
                0.5*preds["roas_6h"] +
                0.3*preds["roas_12h"] +
                0.2*preds["roas_24h"]
            )

            corrected_pred = calibration_model.adjust_prediction(weighted_pred)

            c_score = causal_score(action, graph) if structure["features"]["use_causal"] else 0
            velocity_bonus = (vel+acc) if structure["features"]["use_velocity"] else 0

            campaign_id = action.get("campaign_id")
            campaign_score = campaign_learning.score(campaign_id)
            budget_score = campaign_budget_allocator.get_budget(campaign_id)

            context_features = _context_features(state, action)
            bandit_w = bandit_weight(action, graph, context=context_features, confidence=confidence)

            weights = structure["weights"]

            score = (
                weights["world_model"] * corrected_pred +
                weights["causal"] * c_score +
                weights["velocity"] * velocity_bonus +
                weights["advantage"] * bandit_w
            )

            score += CAMPAIGN_WEIGHT * campaign_score
            score += BUDGET_WEIGHT * budget_score

            decision_row = {
                "action":action,
                "score":score,
                "pred": corrected_pred,
                "strategy": name,
                "campaign_id": campaign_id,
                "structure": structure,
                "context_features": context_features,
                "causal_insights": getattr(state, "causal_insights", {}),
            }
            decisions.append(apply_confidence(decision_row, confidence))

    # Optional MABWiser contextual ranking boost (falls back to score-only sorting).
    selected = recommend_action(
        [d.get("action", {}) for d in decisions],
        _context_features(state),
    )
    if selected is not None:
        for decision in decisions:
            if decision.get("action") == selected:
                decision["score"] += 0.25
                break

    decisions.sort(key=lambda x:x["score"],reverse=True)

    return decisions
