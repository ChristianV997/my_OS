"""core.anomaly.features — feature builder for anomaly detection.

Extracts a fixed-length numeric feature vector from a campaign state dict.
"""
from __future__ import annotations

from typing import Any


_FEATURE_KEYS = ("roas", "ctr", "cvr", "spend", "revenue")


def build_features(state: dict[str, Any]) -> list[float]:
    """Extract a numeric feature vector from *state*.

    Returns a list of floats in a fixed, deterministic order.
    Missing keys default to 0.0.
    """
    return [float(state.get(k, 0.0)) for k in _FEATURE_KEYS]
