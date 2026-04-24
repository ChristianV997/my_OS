"""Experience replay buffer for offline learning from historical transitions.

Supports optional JSON-file persistence so that experiences survive process
restarts (preventing cold-reset loss of learned signal).
"""
from __future__ import annotations

import json
import logging
import os
import random
from collections import deque
from typing import Any

_log = logging.getLogger(__name__)

_DEFAULT_PERSIST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "state", "replay_buffer.json"
)


class ReplayBuffer:
    """Fixed-size circular buffer that stores (state_features, action, reward) tuples.

    Samples are drawn uniformly at random, enabling stable mini-batch updates
    for value function and bandit models without catastrophic forgetting.

    Parameters
    ----------
    capacity:
        Maximum number of experiences to retain.
    persist_path:
        Optional filesystem path for JSON persistence.  When set the buffer
        loads existing experiences on construction and saves after every
        ``add`` / ``add_batch`` call.  Pass ``None`` to disable persistence.
    """

    def __init__(
        self,
        capacity: int = 10_000,
        persist_path: str | None = None,
    ):
        self._buf: deque = deque(maxlen=capacity)
        self.capacity = capacity
        self._persist_path = persist_path

        if persist_path:
            self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load experiences from the JSON file (silently ignores missing/corrupt files)."""
        path = self._persist_path
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
            entries = data if isinstance(data, list) else []
            for entry in entries[-self.capacity:]:
                if isinstance(entry, dict) and "state" in entry and "action" in entry:
                    self._buf.append(entry)
            _log.debug("ReplayBuffer: loaded %d experiences from %s", len(self._buf), path)
        except Exception as exc:  # noqa: BLE001
            _log.warning("ReplayBuffer: could not load %s — %s", path, exc)

    def save(self) -> None:
        """Persist the current buffer to the JSON file."""
        path = self._persist_path
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w") as fh:
                json.dump(list(self._buf), fh)
        except Exception as exc:  # noqa: BLE001
            _log.warning("ReplayBuffer: could not save %s — %s", path, exc)

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
        if self._persist_path:
            self.save()

    def add_batch(self, experiences: list[dict]) -> None:
        """Push a list of experience dicts (each must have state/action/reward keys)."""
        for exp in experiences:
            self._buf.append(
                {
                    "state": list(exp.get("state", [])),
                    "action": exp.get("action", {}),
                    "reward": float(exp.get("reward", 0.0)),
                }
            )
        if self._persist_path:
            self.save()

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


# ---------------------------------------------------------------------------
# Module-level singleton used by the execution loop.
# Persistence is disabled by default so that tests are not I/O-bound; the
# API startup hook enables it after loading config.
# ---------------------------------------------------------------------------

replay_buffer = ReplayBuffer()
