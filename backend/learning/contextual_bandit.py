"""Backend wrapper for the LinUCB contextual bandit from core/.

Provides a single module-level bandit instance pre-configured with the
feature vector used by the execution loop, and a convenience function
``select_arm`` / ``record_reward`` for easy wiring.
"""
import numpy as np

from core.contextual_bandit import LinUCB

# Feature vector: [velocity, acceleration, trend, capital_norm, regime_int]
_N_FEATURES = 5
_ARMS = ["scale", "hold", "pause", "launch_new", "kill"]

# Singleton instance shared across the backend process
_bandit: LinUCB = LinUCB(n_features=_N_FEATURES, arms=_ARMS, alpha=1.0)


def _encode_context(state) -> list:
    """Extract a numeric feature vector from a SystemState-like object."""
    history = [r.get("roas", 0.0) for r in getattr(state.event_log, "rows", [])[-10:]]

    def _velocity(h):
        if len(h) < 2:
            return 0.0
        return float(h[-1] - h[0]) / max(len(h) - 1, 1)

    def _acceleration(h):
        if len(h) < 3:
            return 0.0
        mid = len(h) // 2
        first_half = h[:mid] or [0.0]
        second_half = h[mid:] or [0.0]
        return float(sum(second_half) / len(second_half) - sum(first_half) / len(first_half))

    _REGIME_MAP = {"growth": 1, "stable": 0, "volatile": -1, "decay": -2, "unknown": 0}

    vel = _velocity(history)
    acc = _acceleration(history)
    trend = float(getattr(state, "trend", 0.0))
    capital = min(1.0, max(-1.0, (getattr(state, "capital", 1000.0) - 1000.0) / 1000.0))
    regime_raw = getattr(state, "detected_regime", "unknown")
    regime_int = float(_REGIME_MAP.get(regime_raw, 0)) / 2.0  # normalise to [-1, 1]

    return [vel, acc, trend, capital, regime_int]


def select_arm(state) -> str:
    """Choose the best action arm given the current system state context."""
    x = _encode_context(state)
    return _bandit.choose(x)


def record_reward(arm: str, state, reward: float) -> None:
    """Update the LinUCB parameters after observing a reward."""
    x = _encode_context(state)
    _bandit.update(arm, x, reward)


def bandit_instance() -> LinUCB:
    """Expose the underlying LinUCB for serialisation / inspection."""
    return _bandit
