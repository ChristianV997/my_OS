import json

import numpy as np


def _canonicalize_action(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            normalized[str(key)] = _canonicalize_action(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonicalize_action(item) for item in value]
    if hasattr(value, "item"):
        try:
            item_value = value.item()
            if item_value is value:
                return str(value)
            return _canonicalize_action(item_value)
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)


class BanditMemory:

    def __init__(self):
        self.history = {}  # action_key -> list of rewards

    def _key(self, action):
        if isinstance(action, dict):
            return json.dumps(_canonicalize_action(action), sort_keys=True)
        return str(action)

    def update(self, action, reward):
        k = self._key(action)
        if k not in self.history:
            self.history[k] = []
        self.history[k].append(reward)

    def stats(self, action):
        k = self._key(action)
        vals = self.history.get(k, [])
        if len(vals) == 0:
            return {"mean": 0, "var": 1}
        return {
            "mean": float(np.mean(vals)),
            "var": float(np.var(vals))
        }


bandit_memory = BanditMemory()


def update_from_delayed(delayed_items):

    for item in delayed_items:
        action = item["decision"]
        outcome = item["outcome"]
        roas = outcome.get("roas", 0)

        bandit_memory.update(action, roas)



def bandit_weight(action, graph):

    stats = bandit_memory.stats(action)

    mean = stats["mean"]
    var = stats["var"]

    stability = 1 / (1 + var)

    causal_align = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            causal_align += w

    return mean + stability + causal_align
