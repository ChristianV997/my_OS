import random

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence


store = DelayedRewardStore()

# Stochastic market environment — regime-driven trend with noise
ENV = {"trend": 0.0, "regime": "stable"}

COST_PER_DECISION = 100.0


def _simulate_environment():
    if random.random() < 0.05:
        ENV["regime"] = random.choice(["growth", "decay", "volatile", "stable"])
    if ENV["regime"] == "growth":
        ENV["trend"] += random.uniform(0.01, 0.05)
    elif ENV["regime"] == "decay":
        ENV["trend"] -= random.uniform(0.01, 0.05)
    elif ENV["regime"] == "volatile":
        ENV["trend"] += random.uniform(-0.1, 0.1)
    elif ENV["regime"] == "stable":
        ENV["trend"] *= 0.95  # decay toward zero
    ENV["trend"] = max(-1.0, min(1.0, ENV["trend"]))


def _generate_roas():
    _simulate_environment()
    base = 1.0 + ENV["trend"]
    noise = random.uniform(-0.3, 0.3)
    delayed = random.uniform(-0.1, 0.1)
    return max(0.1, base + noise + delayed)


def execute(decisions, state):
    results = []
    for d in decisions:
        action = d.get("action", {})
        roas = _generate_roas()
        cost = COST_PER_DECISION
        revenue = roas * cost

        # calibration feedback
        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)

        outcome = {
            "roas":     round(roas, 4),
            "roas_6h":  round(max(0.01, roas * random.uniform(0.70, 0.95)), 4),
            "roas_12h": round(max(0.01, roas * random.uniform(0.85, 1.05)), 4),
            "roas_24h": round(max(0.01, roas * random.uniform(0.90, 1.10)), 4),
            "revenue":  round(revenue, 2),
            "cost":     cost,
            "prediction": round(pred, 4),
            "error":    round(pred - roas, 4),
            "env_regime": ENV["regime"],
            "env_trend":  round(ENV["trend"], 4),
        }
        outcome.update(action)

        store.log(action, outcome)
        state.capital += revenue - cost
        results.append(outcome)
    return results


def process_delayed():
    for delay in [5, 10, 20]:
        ready = store.get_ready(delay)
        if ready:
            update_from_delayed(ready)


def run_cycle(state):
    decisions = decide(state)
    results = execute(decisions, state)
    state.event_log.log_batch(results)

    state = learn(state, results)
    state.graph = update_causal(state.graph, state.event_log)

    # update regime detection and track confidence
    prev_regime = state.detected_regime
    state.detected_regime = detector.detect(state.event_log)
    regime_confidence.update(state.detected_regime, ENV["regime"])

    # log calibration stats
    calibration_log.log(calibration_model.stats())

    process_delayed()
    state.total_cycles += 1
    return state
