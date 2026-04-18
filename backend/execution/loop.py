import numpy as np

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.causal.update import update_causal


store = DelayedRewardStore()

# Each variant has a distinct base ROAS and volatility profile
VARIANT_PROFILES = {
    1: {"base_roas": 1.0, "volatility": 0.15},
    2: {"base_roas": 1.3, "volatility": 0.20},
    3: {"base_roas": 1.5, "volatility": 0.25},
    4: {"base_roas": 1.1, "volatility": 0.10},
    5: {"base_roas": 1.4, "volatility": 0.30},
}

COST_PER_DECISION = 10.0


def _simulate_outcome(action):
    variant = action.get("variant", 1)
    profile = VARIANT_PROFILES.get(variant, VARIANT_PROFILES[1])
    roas = max(0.01, np.random.normal(profile["base_roas"], profile["volatility"]))
    cost = COST_PER_DECISION
    return {
        "roas": round(roas, 4),
        "roas_6h": round(max(0.01, roas * np.random.uniform(0.70, 0.95)), 4),
        "roas_12h": round(max(0.01, roas * np.random.uniform(0.85, 1.05)), 4),
        "roas_24h": round(max(0.01, roas * np.random.uniform(0.90, 1.10)), 4),
        "revenue": round(roas * cost, 2),
        "cost": cost,
    }


def execute(decisions, state):
    results = []
    for d in decisions:
        action = d.get("action", {})
        outcome = _simulate_outcome(action)
        outcome.update(action)
        store.log(action, outcome)
        state.capital += outcome["revenue"] - outcome["cost"]
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
    process_delayed()
    return state
