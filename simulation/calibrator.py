"""simulation.calibrator — wrap WorldModelCalibrator for simulation bias correction.

Maintains a per-product calibration state comparing predicted vs actual ROAS.
Provides corrected predictions and tracks calibration quality metrics.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

_log = logging.getLogger(__name__)


class SimulationCalibrator:
    """Thin wrapper around WorldModelCalibrator with per-product sharding.

    Uses a global calibrator for overall bias and product-specific calibrators
    for product-level correction when enough data is available.

    Thread-safe via a single lock.
    """

    _MIN_UPDATES = 5  # product calibrator activates after this many updates

    def __init__(self):
        self._lock = threading.Lock()
        self._global = _make_calibrator()
        self._by_product: dict[str, Any] = {}  # product → WorldModelCalibrator

    # ------------------------------------------------------------------
    # Recording outcomes
    # ------------------------------------------------------------------

    def record(self, product: str, predicted_roas: float, actual_roas: float) -> None:
        """Update calibrators with one (predicted, actual) pair."""
        with self._lock:
            self._global.update(predicted_roas, actual_roas)
            cal = self._by_product.get(product)
            if cal is None:
                cal = _make_calibrator()
                self._by_product[product] = cal
            cal.update(predicted_roas, actual_roas)

    # ------------------------------------------------------------------
    # Correction
    # ------------------------------------------------------------------

    def correct(self, product: str, predicted_roas: float) -> float:
        """Return bias-corrected predicted ROAS.

        Uses product-level calibrator if it has enough updates, otherwise
        falls back to the global calibrator.
        """
        with self._lock:
            cal = self._by_product.get(product)
            if cal is not None and cal.total_updates >= self._MIN_UPDATES:
                return float(cal.correct_prediction(predicted_roas))
            return float(self._global.correct_prediction(predicted_roas))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        with self._lock:
            global_stats = self._global.stats()
            return {
                "global": global_stats,
                "products": {
                    p: c.stats()
                    for p, c in self._by_product.items()
                    if c.total_updates >= self._MIN_UPDATES
                },
                "total_products_calibrated": sum(
                    1 for c in self._by_product.values()
                    if c.total_updates >= self._MIN_UPDATES
                ),
            }

    def report(self) -> dict:
        """Human-readable calibration health report."""
        s = self.stats()
        g = s["global"]
        return {
            "bias_mean": round(g.get("bias_mean", 0), 4),
            "bias_std": round(g.get("bias_std", g.get("rmse", 0)), 4),
            "rmse": round(g.get("rmse", 0), 4),
            "total_updates": g.get("total_updates", 0),
            "products_calibrated": s["total_products_calibrated"],
            "ready": g.get("total_updates", 0) >= self._MIN_UPDATES,
        }


# ── factory helper ────────────────────────────────────────────────────────────

def _make_calibrator():
    try:
        from backend.learning.world_model_calibration import WorldModelCalibrator
        return WorldModelCalibrator(prior_mean=0.0, prior_var=1.0, obs_var=0.5)
    except Exception as exc:
        _log.warning("WorldModelCalibrator_unavailable fallback=NullCalibrator error=%s", exc)
        return _NullCalibrator()


class _NullCalibrator:
    """No-op calibrator used when backend.learning is unavailable."""
    total_updates = 0

    def update(self, predicted: float, actual: float) -> None:
        self.total_updates += 1

    def correct_prediction(self, pred: float) -> float:
        return pred

    def stats(self) -> dict:
        return {"total_updates": self.total_updates, "bias_mean": 0.0, "rmse": 0.0}


# module-level singleton
simulation_calibrator = SimulationCalibrator()
