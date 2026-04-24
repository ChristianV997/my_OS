"""Experience replay buffer for offline learning from historical transitions."""
import random
from collections import deque


class ReplayBuffer:
    """Fixed-size circular buffer that stores (state_features, action, reward) tuples.

    Samples are drawn uniformly at random, enabling stable mini-batch updates
    for value function and bandit models without catastrophic forgetting.
    """

    def __init__(self, capacity: int = 10_000):
        self._buf: deque = deque(maxlen=capacity)
        self.capacity = capacity

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add(self, state_features: list, action: dict, reward: float) -> None:
        """Push one experience tuple into the buffer."""
        self._buf.append(
            {
                "state": list(state_features),
                "action": action,
                "reward": float(reward),
            }
        )

    def add_batch(self, experiences: list[dict]) -> None:
        """Push a list of experience dicts (each must have state/action/reward keys)."""
        for exp in experiences:
            self.add(exp["state"], exp["action"], exp.get("reward", 0.0))

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def sample(self, n: int) -> list[dict]:
        """Return up to *n* randomly sampled experiences (without replacement)."""
        k = min(n, len(self._buf))
        if k == 0:
            return []
        return random.sample(list(self._buf), k)

    def __len__(self) -> int:
        return len(self._buf)

    def is_ready(self, min_size: int = 32) -> bool:
        """True once the buffer has enough entries for a meaningful sample."""
        return len(self._buf) >= min_size


# Module-level singleton used by the execution loop
replay_buffer = ReplayBuffer()
