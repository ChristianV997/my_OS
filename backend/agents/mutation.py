import random


def mutate_action(action):
    a = action.copy()

    # mutate intensity
    if "intensity" in a:
        a["intensity"] *= random.uniform(0.8, 1.2)
        a["intensity"] = max(0.05, min(1.5, a["intensity"]))

    # mutate variant bias
    if "variant" in a:
        shift = random.choice([-1, 0, 1])
        a["variant"] = max(1, min(5, a["variant"] + shift))

    return a


def mutate_strategy(strategy):
    # wrap original propose
    original = strategy.propose

    def mutated_propose(state):
        actions = original(state)
        return [mutate_action(a) for a in actions]

    strategy.propose = mutated_propose

    return strategy
