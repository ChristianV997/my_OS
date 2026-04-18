import logging
import random

from backend.decision.engine import decide
from backend.decision.budget_allocator import allocate as budget_allocate, allocation_summary
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.learning.calibration_log import calibration_log
from backend.causal.update import update_causal
from backend.regime.detector import detector
from backend.regime.confidence import regime_confidence
from backend.agents.structural_evolution import structural_engine
from backend.agents.self_healing import self_healing_engine
from backend.simulation.reality_gap import reality_gap_engine

store = DelayedRewardStore()

# Stochastic market environment — regime-driven trend with noise
ENV = {"trend": 0.0, "regime": "stable"}

TOTAL_CYCLE_BUDGET = 500.0  # total spend per cycle, split across all decisions


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
        ENV["trend"] *= 0.95
    ENV["trend"] = max(-1.0, min(1.0, ENV["trend"]))


def _generate_roas():
    _simulate_environment()
    base = 1.0 + ENV["trend"]
    noise = random.uniform(-0.3, 0.3)
    delayed = random.uniform(-0.1, 0.1)
    return max(0.1, base + noise + delayed)


def _population_diversity():
    """Mean pairwise distance across structural population."""
    from backend.agents.structural_evolution import structure_distance
    pop = structural_engine.population
    if len(pop) < 2:
        return 1.0
    dists = [structure_distance(pop[i], pop[j])
             for i in range(len(pop)) for j in range(i + 1, len(pop))]
    return sum(dists) / len(dists)


def execute(decisions, state):
    budgets = budget_allocate(decisions, total_budget=TOTAL_CYCLE_BUDGET)
    logging.getLogger(__name__).debug(allocation_summary(decisions, budgets))

    results = []
    for i, d in enumerate(decisions):
        action = d.get("action", {})
        structure = d.get("structure")
        roas = _generate_roas()
        cost = round(budgets[i], 4)
        revenue = roas * cost

        pred = d.get("pred", 1.0)
        calibration_model.update(pred, roas)

        outcome = {
            "roas":         round(roas, 4),
            "roas_6h":      round(max(0.01, roas * random.uniform(0.70, 0.95)), 4),
            "roas_12h":     round(max(0.01, roas * random.uniform(0.85, 1.05)), 4),
            "roas_24h":     round(max(0.01, roas * random.uniform(0.90, 1.10)), 4),
            "revenue":      round(revenue, 2),
            "cost":         cost,
            "prediction":   round(pred, 4),
            "error":        round(pred - roas, 4),
            "pred_lo":      d.get("pred_lo"),
            "pred_hi":      d.get("pred_hi"),
            "pred_width":   d.get("pred_width"),
            "interval_conf": d.get("interval_conf"),
            "env_regime":   ENV["regime"],
            "env_trend":    round(ENV["trend"], 4),
        }
        outcome.update(action)

        # structural evolution scoring
        if structure:
            structural_engine.score(structure, roas)

        # track reality gap (real_roas=None until external data arrives)
        reality_gap_engine.update(roas, None)

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
    # initialize structural population on first cycle
    if not structural_engine.population:
        structural_engine.initialize(n=5)

    decisions = decide(state)
    results = execute(decisions, state)
    state.event_log.log_batch(results)

    state = learn(state, results)
    state.graph = update_causal(state.graph, state.event_log)

    state.detected_regime = detector.detect(state.event_log)
    regime_confidence.update(state.detected_regime, ENV["regime"])
    calibration_log.log(calibration_model.stats())

    process_delayed()

    # structural evolution every 10 cycles
    if state.total_cycles % 10 == 0 and state.total_cycles > 0:
        structural_engine.evolve()
        avg_roas = (sum(r.get("roas", 0) for r in results) / max(len(results), 1))
        diversity = _population_diversity()
        self_healing_engine.heal(avg_roas, diversity, structural_engine)

    state.total_cycles += 1
    return state
