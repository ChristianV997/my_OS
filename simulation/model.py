"""simulation.model — Ridge-based pre-execution scoring model.

Trains on historical event rows (roas, ctr, cvr, label) and predicts a
composite engagement score for new candidates.  Falls back to a heuristic
score when insufficient data is available.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from simulation.features import FEATURE_NAMES, batch_extract, extract

_log = logging.getLogger(__name__)

_MIN_ROWS = 20  # minimum history rows before training


def _engagement_target(row: dict) -> float:
    """0–1 composite target from historical event row."""
    roas = float(row.get("roas", 0) or 0)
    ctr = float(row.get("ctr", 0) or 0)
    cvr = float(row.get("cvr", 0) or 0)
    # normalise against typical maxima
    r = min(roas / 3.0, 1.0)
    c = min(ctr / 0.05, 1.0)
    v = min(cvr / 0.04, 1.0)
    return 0.5 * r + 0.3 * c + 0.2 * v


class ScoringModel:
    """Ridge regression scorer with online retraining.

    Thread-safe: all public methods acquire ``_lock``.
    """

    def __init__(self, alpha: float = 1.0):
        self._alpha = alpha
        self._ridge: Ridge | None = None
        self._scaler = StandardScaler()
        self._fitted = False
        self._lock = threading.Lock()
        self._train_count = 0

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        rows: list[dict],
        patterns: dict | None = None,
        playbooks: dict | None = None,
    ) -> bool:
        """Train on historical event rows. Returns True if trained."""
        if len(rows) < _MIN_ROWS:
            return False

        history_map: dict[str, list[dict]] = {}
        for r in rows:
            p = r.get("product", "")
            history_map.setdefault(p, []).append(r)

        # Build signal-like dicts from event rows for feature extraction
        signals = [
            {
                "product": r.get("product", ""),
                "score": float(r.get("roas", 0) or 0) / 3.0,
                "velocity": float(r.get("velocity", 0) or 0),
                "hook": r.get("hook", ""),
                "angle": r.get("angle", ""),
                "regime": r.get("env_regime", ""),
                "engagement_rate": float(r.get("engagement_rate", 0) or 0),
            }
            for r in rows
        ]

        X_raw = batch_extract(signals, patterns=patterns, playbooks=playbooks,
                              history_map=history_map)
        y = [_engagement_target(r) for r in rows]

        X = np.array(X_raw, dtype=float)
        y_arr = np.array(y, dtype=float)

        with self._lock:
            try:
                X_scaled = self._scaler.fit_transform(X)
                ridge = Ridge(alpha=self._alpha)
                ridge.fit(X_scaled, y_arr)
                self._ridge = ridge
                self._fitted = True
                self._train_count += 1
                return True
            except Exception as exc:
                _log.warning("scoring_model_fit_failed error=%s", exc)
                return False

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        signals: list[dict],
        patterns: dict | None = None,
        playbooks: dict | None = None,
        history_map: dict[str, list[dict]] | None = None,
    ) -> list[float]:
        """Return predicted engagement scores in [0, 1] for each signal."""
        if not signals:
            return []

        X_raw = batch_extract(signals, patterns=patterns, playbooks=playbooks,
                              history_map=history_map)
        X = np.array(X_raw, dtype=float)

        with self._lock:
            if self._fitted and self._ridge is not None:
                try:
                    X_scaled = self._scaler.transform(X)
                    raw = self._ridge.predict(X_scaled)
                    return [float(np.clip(v, 0.0, 1.0)) for v in raw]
                except Exception as exc:
                    _log.warning("scoring_model_predict_failed error=%s", exc)

        # Fallback: heuristic from feature vector
        return [_heuristic_score(fv) for fv in X_raw]

    def predict_one(
        self,
        signal: dict,
        patterns: dict | None = None,
        playbook: Any | None = None,
        history: list[dict] | None = None,
    ) -> float:
        fv = extract(signal, patterns=patterns, playbook=playbook, history=history)
        X = np.array([fv], dtype=float)
        with self._lock:
            if self._fitted and self._ridge is not None:
                try:
                    X_scaled = self._scaler.transform(X)
                    return float(np.clip(self._ridge.predict(X_scaled)[0], 0.0, 1.0))
                except Exception:
                    pass
        return _heuristic_score(fv)

    @property
    def is_fitted(self) -> bool:
        with self._lock:
            return self._fitted

    def info(self) -> dict:
        with self._lock:
            return {
                "fitted": self._fitted,
                "train_count": self._train_count,
                "feature_names": FEATURE_NAMES,
                "n_features": len(FEATURE_NAMES),
            }


# ── heuristic fallback ────────────────────────────────────────────────────────

def _heuristic_score(fv: list[float]) -> float:
    """Weighted sum of key features as a cold-start fallback."""
    # indices: signal_score=0, hook_score=2, angle_score=3,
    #          playbook_estimated_roas=5, hist_avg_roas=8, hist_win_rate=11
    weights = {0: 0.30, 2: 0.15, 3: 0.10, 5: 0.20, 8: 0.20, 11: 0.05}
    score = sum(fv[i] * w for i, w in weights.items() if i < len(fv))
    return float(max(0.0, min(1.0, score)))


# module-level singleton
scoring_model = ScoringModel()
