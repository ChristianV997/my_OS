import time

from backend.decision.engine import decide
from backend.learning.delayed_rewards import DelayedRewardStore
from backend.learning.bandit_update import update_from_delayed


store = DelayedRewardStore()


def execute(decisions, state):
    results = []

    for d in decisions:

        outcome = {"roas": 1.2, "revenue": 100, "cost": 80}

        # log for delayed evaluation
        store.log(d["action"], outcome)

        results.append(outcome)

    return results


def process_delayed():

    # simulate different horizons (seconds for now)
    delays = [5, 10, 20]

    for d in delays:
        ready = store.get_ready(d)
        if ready:
            update_from_delayed(ready)


def run_cycle(state):

    decisions = decide(state)

    results = execute(decisions, state)

    state.event_log.log_batch(results)

    # process delayed rewards each cycle
    process_delayed()

    return state
