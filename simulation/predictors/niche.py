"""simulation.predictors.niche — product/niche virality predictor.

Estimates the virality potential of a product niche using:
  1. Current signal score from SignalEngine
  2. Historical win rate from replay store
  3. Playbook confidence for the product
  4. Velocity (momentum) from signal data

Combines these into a 0–1 virality score without any ML —
just a weighted average of interpretable features.
"""
from __future__ import annotations

import threading


class NichePredictor:
    """Predict virality score for a product/niche.

    Weights:
      0.35 — signal score (how strong the current market signal is)
      0.25 — historical win rate (WINNER / total outcomes for this product)
      0.25 — playbook confidence (evidence-backed strategy exists)
      0.15 — velocity (signal momentum)
    """

    def __init__(self):
        self._lock = threading.Lock()

    def score(self, product: str, signal_score: float = 0.0,
              velocity: float = 0.0) -> float:
        """Return a 0–1 virality estimate for a product."""
        # historical win rate from replay store
        hist_wr = self._win_rate(product)
        # playbook confidence
        pb_conf = self._playbook_confidence(product)

        virality = (
            0.35 * min(signal_score, 1.0)
            + 0.25 * hist_wr
            + 0.25 * pb_conf
            + 0.15 * min(velocity, 1.0)
        )
        return float(max(0.0, min(1.0, virality)))

    def score_signal(self, signal: dict) -> float:
        """Convenience: score from a raw signal dict."""
        return self.score(
            product=signal.get("product", ""),
            signal_score=float(signal.get("score", 0)),
            velocity=float(signal.get("velocity", 0)),
        )

    def _win_rate(self, product: str) -> float:
        try:
            from simulation.replay import replay_store
            stats = replay_store.winner_rate(product=product)
            return float(stats.get("win_rate", 0.0))
        except Exception:
            return 0.0

    def _playbook_confidence(self, product: str) -> float:
        try:
            from core.content.playbook import playbook_memory
            pb = playbook_memory.get(product)
            if pb is not None:
                return float(getattr(pb, "confidence", 0.0))
        except Exception:
            pass
        return 0.0


# module-level singleton
niche_predictor = NichePredictor()
