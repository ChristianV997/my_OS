import json
from collections import OrderedDict

import numpy as np

HISTORY_LIMIT = 1000
FIT_EVERY_N = 10


def _stable_key(action):
    try:
        return json.dumps(action, sort_keys=True, default=str)
    except TypeError:
        return str(action)


def _arm_id(action):
    variant = "default"
    intensity = 0.5

    if isinstance(action, dict):
        variant = action.get("variant", "default")
        intensity = action.get("intensity", 0.5)
    elif isinstance(action, (list, tuple)) and action:
        variant = action[0]

    try:
        intensity = float(intensity)
    except (TypeError, ValueError):
        intensity = 0.5

    bucket = "low" if intensity < 0.33 else "high" if intensity > 0.66 else "mid"
    return f"{variant}_{bucket}"


class BanditMemory:

    def __init__(self, maxlen=HISTORY_LIMIT):
        self.maxlen = maxlen
        self.history = {}  # action_key -> list of rewards
        self._key_order = OrderedDict()

    def _key(self, action):
        return _stable_key(action)

    def update(self, action, reward):
        k = self._key(action)
        if k not in self.history:
            self.history[k] = []
        self._key_order[k] = None
        self._key_order.move_to_end(k)

        self.history[k].append(reward)
        if len(self.history[k]) > self.maxlen:
            self.history[k] = self.history[k][-self.maxlen:]

        while len(self.history) > self.maxlen and self._key_order:
            oldest, _ = self._key_order.popitem(last=False)
            self.history.pop(oldest, None)

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
decisions = []
rewards = []
contexts = []
actions_by_arm = {}
_pending_fit_count = 0


def _fit():
    return None


def _prune_actions_by_arm():
    active_arms = set(decisions[-HISTORY_LIMIT:])
    stale_arms = [arm for arm in actions_by_arm if arm not in active_arms]
    for arm in stale_arms:
        actions_by_arm.pop(arm, None)


def observe(action, reward, context=None):
    global _pending_fit_count

    arm = _arm_id(action)
    decisions.append(arm)
    rewards.append(float(reward))
    contexts.append(context)
    actions_by_arm[arm] = action

    if len(decisions) > HISTORY_LIMIT:
        del decisions[:-HISTORY_LIMIT]
    if len(rewards) > HISTORY_LIMIT:
        del rewards[:-HISTORY_LIMIT]
    if len(contexts) > HISTORY_LIMIT:
        del contexts[:-HISTORY_LIMIT]

    _prune_actions_by_arm()

    _pending_fit_count += 1
    if _pending_fit_count >= FIT_EVERY_N:
        _fit()
        _pending_fit_count = 0


def update_from_delayed(delayed_items):

    for item in delayed_items:
        action = item["decision"]
        outcome = item["outcome"]
        roas = outcome.get("roas", 0)

        bandit_memory.update(action, roas)
        observe(action, roas, context=item.get("context"))


def bonus(_action):
    """Disabled: recommendation boost is applied in decision scoring."""
    return 0.0


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
