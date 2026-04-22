import numpy as np

class BanditMemory:

    def __init__(self):
        self.history = {}  # action_key -> list of rewards

    def _key(self, action):
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



def bandit_weight(action, graph, confidence=1.0):

    stats = bandit_memory.stats(action)

    mean = stats["mean"]
    var = stats["var"]
    confidence = max(0.05, min(1.0, confidence))

    stability = 1 / (1 + var)

    causal_align = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            causal_align += w

    exploration_bonus = (1.0 - confidence) * stability
    return confidence * mean + stability + causal_align + exploration_bonus
