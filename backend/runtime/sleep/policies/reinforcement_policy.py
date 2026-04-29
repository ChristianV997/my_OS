"""ReinforcementPolicy — success-weighted score boosting for procedures and patterns.

Implements a simple exponential moving average (EMA) update rule so that
repeated successes compound while isolated successes decay gracefully.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass


_EMA_ALPHA   = float(os.getenv("SLEEP_REINFORCE_ALPHA", "0.3"))   # EMA weight for new obs
_ROAS_SCALE  = float(os.getenv("SLEEP_REINFORCE_ROAS_SCALE", "5.0"))  # ROAS normalization
_MIN_SAMPLES = int(os.getenv("SLEEP_REINFORCE_MIN_SAMPLES", "3"))      # samples before boosting


@dataclass
class ReinforcementPolicy:
    """Controls how successful outcomes boost procedural and semantic scores."""

    ema_alpha:   float = _EMA_ALPHA
    roas_scale:  float = _ROAS_SCALE
    min_samples: int   = _MIN_SAMPLES

    def update_score(
        self,
        current_score: float,
        new_roas: float,
        success: bool,
        sample_count: int = 1,
    ) -> float:
        """Return updated score using EMA with ROAS-weighted signal."""
        if sample_count < self.min_samples:
            return current_score
        signal = (new_roas / self.roas_scale) if success else 0.0
        signal = min(1.0, max(0.0, signal))
        return self.ema_alpha * signal + (1 - self.ema_alpha) * current_score

    def confidence(
        self,
        success_rate: float,
        sample_count: int,
        avg_roas: float = 0.0,
    ) -> float:
        """Return a [0, 1] confidence score for a procedure or pattern.

        Confidence grows with sample_count, success_rate, and ROAS.
        """
        if sample_count == 0:
            return 0.0
        sample_weight = 1 - math.exp(-sample_count / 10.0)
        roas_weight   = min(avg_roas / self.roas_scale, 1.0)
        return sample_weight * (0.6 * success_rate + 0.4 * roas_weight)

    def should_promote(
        self,
        success_rate: float,
        sample_count: int,
        avg_roas: float,
        threshold: float = 0.6,
    ) -> bool:
        """Return True if this procedure/pattern should be elevated in ranking."""
        return self.confidence(success_rate, sample_count, avg_roas) >= threshold

    def should_deprecate(
        self,
        success_rate: float,
        sample_count: int,
        threshold: float = 0.2,
    ) -> bool:
        """Return True if this procedure should be deprecated (below threshold)."""
        if sample_count < self.min_samples:
            return False
        return success_rate < threshold
