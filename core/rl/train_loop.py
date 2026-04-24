"""core.rl.train_loop — RL training step using the experience replay buffer."""
from __future__ import annotations

from core.rl.replay_buffer import ReplayBuffer
from core.rl.trainer import RLTrainer
from core.rl.policy import PolicyNet

buffer = ReplayBuffer()


def train(policy: PolicyNet, trainer: RLTrainer) -> None:
    """Sample a mini-batch from the replay buffer and update the policy.

    Parameters
    ----------
    policy:
        The PolicyNet to update.
    trainer:
        RLTrainer that drives the update step.
    """
    batch = buffer.sample(32)
    if not batch:
        return

    states = [b.get("state", {}) for b in batch]
    actions = [str(b.get("action", "HOLD")) for b in batch]
    rewards = [float(b.get("reward", 0.0)) for b in batch]

    trainer.train_step(states, actions, rewards)
