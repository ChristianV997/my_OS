"""core.rl.policy — simple RL policy wrapper.

PolicyNet is a lightweight policy abstraction.  In the current implementation
it uses a softmax bandit over discrete action scores.  A full neural-network
implementation can replace this as training data accumulates.
"""
from __future__ import annotations

import math
import random
from typing import Any


ACTIONS = ("BUY", "SCALE", "HOLD", "KILL")


class PolicyNet:
    """Softmax-bandit policy over a fixed action set.

    Parameters
    ----------
    temperature:
        Controls exploration.  Higher values → more uniform sampling.
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = temperature
        # Learned score per action (initialised to zero)
        self._scores: dict[str, float] = {a: 0.0 for a in ACTIONS}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_action(self, state: dict[str, Any]) -> str:
        """Return the best action for *state* using softmax probabilities."""
        roas = state.get("roas", 1.0)
        # Simple heuristic to seed scores from the current state
        scores = {
            "BUY":   self._scores["BUY"]  + roas * 0.5,
            "SCALE": self._scores["SCALE"] + roas * 0.3,
            "HOLD":  self._scores["HOLD"]  + 1.0,
            "KILL":  self._scores["KILL"]  + (1.0 - roas) * 0.5,
        }
        return self._softmax_sample(scores)

    def update(self, action: str, reward: float, state: dict[str, Any] | None = None) -> None:
        """Update score for *action* toward *reward* using a moving average.

        If *state* is provided, the ROAS from the state is used to weight the
        update — high-ROAS states contribute more to the scale/buy scores.
        """
        alpha = 0.1
        # State-conditioned weighting: scale reward by relative ROAS
        if state is not None:
            roas = state.get("roas", 1.0)
            reward = reward * max(0.5, min(2.0, roas))
        if action in self._scores:
            self._scores[action] = (1 - alpha) * self._scores[action] + alpha * reward

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _softmax_sample(self, scores: dict[str, float]) -> str:
        exps = {a: math.exp(s / max(self.temperature, 1e-8)) for a, s in scores.items()}
        total = sum(exps.values()) or 1.0
        probs = {a: v / total for a, v in exps.items()}
        r = random.random()
        cumulative = 0.0
        for action, p in probs.items():
            cumulative += p
            if r < cumulative:
                return action
        return max(probs, key=lambda a: probs[a])
