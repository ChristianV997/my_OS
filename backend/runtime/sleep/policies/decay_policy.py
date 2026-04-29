"""DecayPolicy — scoring rules for memory aging and forgetting.

Implements exponential time decay so that older, less-reinforced memories
lose retention weight.  High-ROAS outcomes resist decay; low-signal events
decay faster.

Decay formula:
    retention = base_score * exp(-lambda * age_hours)
    + reinforcement_bonus * success_rate

where lambda is tunable per domain.
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field


# Env-tunable decay constants (hours)
_DEFAULT_LAMBDA = float(os.getenv("SLEEP_DECAY_LAMBDA", "0.01"))   # slow global decay
_DOMAIN_LAMBDAS: dict[str, float] = {
    "hook":      float(os.getenv("SLEEP_DECAY_HOOK",      "0.008")),
    "angle":     float(os.getenv("SLEEP_DECAY_ANGLE",     "0.01")),
    "signal":    float(os.getenv("SLEEP_DECAY_SIGNAL",    "0.05")),  # signals decay fast
    "product":   float(os.getenv("SLEEP_DECAY_PRODUCT",   "0.003")), # products decay slow
    "campaign":  float(os.getenv("SLEEP_DECAY_CAMPAIGN",  "0.02")),
    "procedure": float(os.getenv("SLEEP_DECAY_PROCEDURE", "0.005")),
}
_PRUNE_THRESHOLD = float(os.getenv("SLEEP_PRUNE_THRESHOLD", "0.05"))


@dataclass
class DecayPolicy:
    """Controls how fast memories age and when they are pruned."""

    base_lambda:      float = _DEFAULT_LAMBDA
    prune_threshold:  float = _PRUNE_THRESHOLD
    domain_lambdas:   dict[str, float] = field(default_factory=lambda: dict(_DOMAIN_LAMBDAS))

    def decay_score(
        self,
        base_score: float,
        ts: float,
        domain: str = "",
        success_rate: float = 0.0,
        avg_roas: float = 0.0,
    ) -> float:
        """Return the retention score for a memory unit.

        Higher = more likely to be retained.  Below prune_threshold → prune.
        """
        age_hours = (time.time() - ts) / 3600.0
        lam       = self.domain_lambdas.get(domain, self.base_lambda)
        decayed   = base_score * math.exp(-lam * age_hours)

        # Reinforcement bonus: success rate and ROAS resist decay
        bonus = success_rate * 0.3 + min(avg_roas / 10.0, 0.5)
        return min(1.0, decayed + bonus)

    def should_prune(
        self,
        base_score: float,
        ts: float,
        domain: str = "",
        success_rate: float = 0.0,
        avg_roas: float = 0.0,
    ) -> bool:
        return self.decay_score(
            base_score, ts, domain, success_rate, avg_roas
        ) < self.prune_threshold

    def rank_by_retention(
        self,
        items: list[dict],
        score_key: str = "score",
        ts_key: str = "ts",
        domain_key: str = "domain",
    ) -> list[dict]:
        """Return items sorted descending by retention score."""
        def _ret(item: dict) -> float:
            return self.decay_score(
                base_score=float(item.get(score_key, 0.5)),
                ts=float(item.get(ts_key, time.time())),
                domain=str(item.get(domain_key, "")),
                success_rate=float(item.get("success_rate", 0.0)),
                avg_roas=float(item.get("avg_roas", 0.0)),
            )
        return sorted(items, key=_ret, reverse=True)
