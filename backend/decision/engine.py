from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight, recommend_action
from backend.learning.calibration import calibration_model
from backend.learning.campaign_learning import campaign_learning
from backend.agents.campaign_budget import campaign_budget_allocator
from backend.agents.structural_evolution import structural_engine
from backend.agents.strategies import strategies
from backend.agents.allocator import allocator
from agents.world_model import world_model

import random

CAMPAIGN_WEIGHT = 0.5
BUDGET_WEIGHT = 0.3
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


def _base_context(state, rows):
    """Compute state-level context features once per decide() call."""
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
    }, vel, acc


def _action_context(base, action):
    """Extend cached base context with per-action features."""
    ctx = base.copy()
    ctx["variant"] = float(action.get("variant", 0))
    ctx["intensity"] = float(action.get("intensity", 0))
    return ctx


def decide(state):

    if not structural_engine.population:
        structural_engine.initialize()

    structure = random.choice(structural_engine.population)
    graph = _safe_graph(state)
    rows = _safe_rows(state)

    if hasattr(state, "event_log"):
        world_model.train(state.event_log)

    # Compute velocity/acceleration once and reuse from cached base context.
    base_ctx, vel, acc = _base_context(state, rows)

    decisions = []

    total_budget = 10

    strategy_pool = getattr(state, "strategies", None) or strategies

    for name, strat in strategy_pool.items():

        n_actions = allocator.allocate(name, total_budget)
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

            context_features = _action_context(base_ctx, action)
            bandit_w = bandit_weight(action, graph, context_features)

            confidence = calibration_model.confidence_weight()

            weights = structure["weights"]

            score = (
                weights["world_model"] * corrected_pred +
                weights["causal"] * c_score +
                weights["velocity"] * velocity_bonus +
                weights["advantage"] * bandit_w
            ) * confidence

            score += CAMPAIGN_WEIGHT * campaign_score
            score += BUDGET_WEIGHT * budget_score

            decisions.append({
                "action": action,
                "score": score,
                "pred": corrected_pred,
                "strategy": name,
                "campaign_id": campaign_id,
                "structure": structure,
                "context_features": context_features,
                "causal_insights": getattr(state, "causal_insights", {}),
            })

    # Optional MABWiser contextual ranking boost (falls back to score-only sorting).
    recommend_ctx = base_ctx.copy()
    recommend_ctx.setdefault("variant", 0.0)
    recommend_ctx.setdefault("intensity", 0.0)
    selected = recommend_action(
        [d.get("action", {}) for d in decisions],
        recommend_ctx,
    )
    if selected is not None:
        for decision in decisions:
            if decision.get("action") == selected:
                decision["score"] += 0.25
                break

    decisions.sort(key=lambda x: x["score"], reverse=True)

    return decisions
