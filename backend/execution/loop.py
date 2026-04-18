import time
import random

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.causal.update import update_causal


store = DelayedRewardStore()

# global environment state
ENV = {
    "trend": 0.0,
    "regime": "stable"
}


def simulate_environment():

    # regime shift
    if random.random() < 0.05:
        ENV["regime"] = random.choice(["growth", "decay", "volatile"])

    # trend dynamics
    if ENV["regime"] == "growth":
        ENV["trend"] += random.uniform(0.01, 0.05)
    elif ENV["regime"] == "decay":
        ENV["trend"] -= random.uniform(0.01, 0.05)
    elif ENV["regime"] == "volatile":
        ENV["trend"] += random.uniform(-0.1, 0.1)

    # clamp trend
    ENV["trend"] = max(-1, min(1, ENV["trend"]))

    return ENV


def generate_roas():

    env = simulate_environment()

    base = 1.0

    # noise
    noise = random.uniform(-0.3, 0.3)

    # delayed effect simulation
    delayed = random.uniform(-0.1, 0.1)

    roas = base + env["trend"] + noise + delayed

    return max(0.1, roas)


def execute(decisions, state):
    results = []

    for d in decisions:

        roas = generate_roas()

        outcome = {
            "roas": roas,
            "revenue": 100 * roas,
            "cost": 100
        }

        outcome.update(d.get("action", {}))

        # calibration update
        pred = d.get("pred", 1.0)
        actual = outcome.get("roas", 0)
        calibration_model.update(pred, actual)

        outcome["prediction"] = pred
        outcome["error"] = pred - actual
        outcome["regime"] = ENV["regime"]
        outcome["trend"] = ENV["trend"]

        store.log(d["action"], outcome)

        results.append(outcome)

    return results


def process_delayed():

    delays = [5, 10, 20]

    for d in delays:
        ready = store.get_ready(d)
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
