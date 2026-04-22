import json
import os

import numpy as np

try:
    from mabwiser.mab import MAB, LearningPolicy
    MABWISER_AVAILABLE = True
except Exception:
    MAB = None
    LearningPolicy = None
    MABWISER_AVAILABLE = False

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


class ContextualBanditModel:
    HISTORY_LIMIT = 500
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
        self.decisions = []
        self.rewards = []
        self.contexts = []

    def _arm(self, action):
        return json.dumps(action, sort_keys=True)

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

        self.model = MAB(arms=arms, learning_policy=self._learning_policy(), seed=self.DEFAULT_SEED)
        try:
            self.model.fit(self.decisions, self.rewards, contexts=self.contexts)
        except TypeError:
            self.model.fit(self.decisions, self.rewards)
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
        self.decisions = self.decisions[-self.HISTORY_LIMIT:]
        self.rewards = self.rewards[-self.HISTORY_LIMIT:]
        self.contexts = self.contexts[-self.HISTORY_LIMIT:]
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

        bandit_memory.update(action, roas)
        contextual_bandit.observe(action, roas, context)


def update_from_results(decisions, outcomes):
    for decision, outcome in zip(decisions, outcomes):
        action = decision.get("action", {})
        context = decision.get("context_features", {})
        roas = outcome.get("roas", 0)
        bandit_memory.update(action, roas)
        contextual_bandit.observe(action, roas, context)


def recommend_action(candidate_actions, context):
    return contextual_bandit.recommend(candidate_actions, context)

def bandit_weight(action, graph, confidence=1.0, context=None):

    stats = bandit_memory.stats(action)

    mean = stats["mean"]
    var = stats["var"]
    confidence = max(0.05, min(1.0, confidence))

    stability = 1 / (1 + var)

    causal_align = 0
    for (p, c), w in graph.edges.items():
        if p in action:
            causal_align += w

    mab_bonus = contextual_bandit.bonus(action, context)

    exploration_bonus = (1.0 - confidence) * stability
    return confidence * mean + stability + causal_align + exploration_bonus + mab_bonus
