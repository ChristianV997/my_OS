import json
import os
from collections import deque

import numpy as np

try:
    from mabwiser.mab import MAB, LearningPolicy
    MABWISER_AVAILABLE = True
except Exception:
    MAB = None
    LearningPolicy = None
    MABWISER_AVAILABLE = False


class BanditMemory:
    MAX_HISTORY_PER_KEY = 200

    def __init__(self):
        self.history = {}  # action_key -> list of rewards

    def _key(self, action):
        return str(action)

    def update(self, action, reward):
        k = self._key(action)
        if k not in self.history:
            self.history[k] = []
        vals = self.history[k]
        vals.append(reward)
        if len(vals) > self.MAX_HISTORY_PER_KEY:
            self.history[k] = vals[-self.MAX_HISTORY_PER_KEY:]

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


class ContextualBanditModel:
    HISTORY_LIMIT = 500
    REFIT_INTERVAL = 5
    DEFAULT_SEED = int(os.getenv("MABWISER_SEED", "7"))

    CONTEXT_KEYS = [
        "regime_code",
        "detected_regime_code",
        "capital",
        "recent_roas",
        "roas_velocity",
        "roas_acceleration",
        "causal_roas_effect",
        "cycle",
        "variant",
        "intensity",
    ]

    def __init__(self):
        self.model = None
        self.is_fitted = False
        self.actions_by_arm = {}
        self.decisions = deque(maxlen=self.HISTORY_LIMIT)
        self.rewards = deque(maxlen=self.HISTORY_LIMIT)
        self.contexts = deque(maxlen=self.HISTORY_LIMIT)
        self._obs_since_fit = 0

    def _arm(self, action):
        try:
            return json.dumps(action, sort_keys=True)
        except (TypeError, ValueError):
            return str(action)

    def _vectorize(self, context):
        context = context or {}
        return [float(context.get(k, 0.0)) for k in self.CONTEXT_KEYS]

    def _learning_policy(self):
        policy = os.getenv("MABWISER_POLICY", "linucb").strip().lower()
        if policy == "thompson":
            return LearningPolicy.ThompsonSampling()
        if policy == "ucb":
            return LearningPolicy.UCB1(alpha=1.0)
        return LearningPolicy.LinUCB(alpha=1.0)

    def _fit(self):
        if not MABWISER_AVAILABLE or len(self.decisions) < 2:
            return

        arms = list(self.actions_by_arm.keys())
        if len(arms) < 2:
            return

        decisions_list = list(self.decisions)
        rewards_list = list(self.rewards)
        contexts_list = list(self.contexts)

        self.model = MAB(arms=arms, learning_policy=self._learning_policy(), seed=self.DEFAULT_SEED)
        try:
            self.model.fit(decisions_list, rewards_list, contexts=contexts_list)
        except TypeError:
            self.model.fit(decisions_list, rewards_list)
        except Exception:
            self.model = None
            self.is_fitted = False
            return

        self.is_fitted = True

    def observe(self, action, reward, context=None):
        arm = self._arm(action)
        self.actions_by_arm[arm] = action
        self.decisions.append(arm)
        self.rewards.append(float(reward))
        self.contexts.append(self._vectorize(context))
        self._obs_since_fit += 1
        # Throttle expensive re-fitting to every REFIT_INTERVAL observations.
        if self._obs_since_fit >= self.REFIT_INTERVAL:
            self._obs_since_fit = 0
            self._fit()

    def recommend(self, candidate_actions, context=None):
        if not (MABWISER_AVAILABLE and self.is_fitted and self.model):
            return None

        candidate_arms = {self._arm(a): a for a in candidate_actions}
        if not candidate_arms:
            return None

        try:
            prediction = self.model.predict(contexts=[self._vectorize(context)])
            arm = prediction[0] if isinstance(prediction, list) else prediction
        except TypeError:
            arm = self.model.predict()
        except Exception:
            return None

        return candidate_arms.get(arm)

    def bonus(self, action, context=None):
        return 0.0


contextual_bandit = ContextualBanditModel()


def _record_bandit_observation(action, roas, context):
    """Shared helper for recording an observation in both bandit memory and contextual model."""
    bandit_memory.update(action, roas)
    contextual_bandit.observe(action, roas, context)


def update_from_delayed(delayed_items):

    for item in delayed_items:
        decision_payload = item["decision"]
        if isinstance(decision_payload, dict) and "action" in decision_payload:
            action = decision_payload.get("action", {})
            context = decision_payload.get("context", {})
        else:
            action = decision_payload
            context = {}
        outcome = item["outcome"]
        roas = outcome.get("roas", 0)

        _record_bandit_observation(action, roas, context)


def update_from_results(decisions, outcomes):
    for decision, outcome in zip(decisions, outcomes):
        action = decision.get("action", {})
        context = decision.get("context_features", {})
        roas = outcome.get("roas", 0)
        _record_bandit_observation(action, roas, context)


def recommend_action(candidate_actions, context):
    return contextual_bandit.recommend(candidate_actions, context)


def bandit_weight(action, graph, context=None):
    """Return a combined score for `action` from memory stats, graph alignment, and optional context.

    Args:
        action: Action payload used as the bandit key.
        graph: Causal graph-like object with an `edges` mapping.
        context: Optional contextual feature dictionary for MABWiser.

    Returns:
        Float score used by the decision engine ranking logic.
    """

    stats = bandit_memory.stats(action)

    mean = stats["mean"]
    var = stats["var"]

    stability = 1 / (1 + var)

    causal_align = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            causal_align += w

    mab_bonus = contextual_bandit.bonus(action, context)

    return mean + stability + causal_align + mab_bonus
