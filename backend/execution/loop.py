import time

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed
from backend.learning.update import learn
from backend.learning.calibration import calibration_model
from backend.causal.update import update_causal


store = DelayedRewardStore()


def execute(decisions, state):
    results = []

    for d in decisions:

        outcome = {"roas": 1.2, "revenue": 100, "cost": 80}

        # attach action context
        outcome.update(d.get("action", {}))

        # calibration update
        pred = d.get("pred", 1.0)
        actual = outcome.get("roas", 0)
        calibration_model.update(pred, actual)

        # store error for learning visibility
        outcome["prediction"] = pred
        outcome["error"] = pred - actual

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

    # learning layer (signals)
    state = learn(state, results)

    # causal update
    state.graph = update_causal(state.graph, state.event_log)

    # delayed rewards
    process_delayed()

    return state
