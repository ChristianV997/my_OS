"""core.rl.trainer — RL training step."""
from __future__ import annotations

from typing import Any

from core.rl.policy import PolicyNet


class RLTrainer:
    """Applies a batch of (state, action, reward) tuples to update a PolicyNet."""

    def __init__(self, policy: PolicyNet | None = None) -> None:
        self.policy = policy or PolicyNet()

    def train_step(
        self,
        states: list[dict[str, Any]],
        actions: list[str],
        rewards: list[float],
    ) -> None:
        """Update the policy for each experience in the batch.

        State context is passed to the policy update so it can condition
        its score adjustments on the observed state.
        """
        for state, action, reward in zip(states, actions, rewards):
            self.policy.update(action, reward, state=state)
