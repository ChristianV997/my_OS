"""core.rl.replay_buffer — lightweight in-memory experience replay buffer.

Wraps the backend ReplayBuffer with a dict-friendly API used by the engine layer.
"""
from __future__ import annotations

from backend.learning.replay_buffer import ReplayBuffer as _BackendBuffer


class ReplayBuffer:
    """Thread-safe in-memory replay buffer with dict-based add API.

    This thin wrapper adapts the backend ReplayBuffer to accept experience
    dicts directly (``{"state": ..., "action": ..., "reward": ...}``).
    """

    def __init__(self, capacity: int = 10_000) -> None:
        self._buf = _BackendBuffer(capacity=capacity, persist_path=None)

    def add(self, experience: dict) -> None:
        """Push one experience dict.

        Parameters
        ----------
        experience:
            Must contain ``state`` (dict), ``action`` (str) and ``reward`` (float).
        """
        state = experience.get("state", {})
        # Convert state dict to a feature list — numeric values only
        if isinstance(state, dict):
            features = []
            for k in sorted(state.keys()):
                v = state[k]
                try:
                    features.append(float(v))
                except (TypeError, ValueError):
                    pass
        else:
            features = list(state)
        self._buf.add(features, experience.get("action", "HOLD"), float(experience.get("reward", 0.0)))

    def sample(self, n: int) -> list[dict]:
        """Return up to *n* randomly sampled experience dicts."""
        return self._buf.sample(n)

    def __len__(self) -> int:
        return len(self._buf)
