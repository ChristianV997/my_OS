"""core.anomaly.model — ML anomaly model (IsolationForest + Z-score hybrid).

Step 55: ML Anomaly Detection + Auto-Response System

Uses IsolationForest as the primary detector with a Z-score fallback when
there is insufficient data to fit the ensemble model (< 10 samples).
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

try:
    from sklearn.ensemble import IsolationForest as _IsolationForest
    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SKLEARN_AVAILABLE = False

_log = logging.getLogger(__name__)

_MIN_SAMPLES_FOR_IF = 10
_Z_SCORE_THRESHOLD = 3.0
_IF_THRESHOLD = -0.2


class AnomalyModel:
    """Hybrid anomaly detector: IsolationForest when trained, Z-score otherwise.

    Parameters
    ----------
    contamination:
        Expected fraction of outliers in training data (IsolationForest param).
    """

    def __init__(self, contamination: float = 0.05) -> None:
        self.contamination = contamination
        self._trained = False
        self._training_data: list[list[float]] = []
        if _SKLEARN_AVAILABLE:
            self._model = _IsolationForest(contamination=contamination)
        else:
            self._model = None  # type: ignore[assignment]

    def fit(self, X: list[list[float]] | np.ndarray) -> None:
        """Fit the IsolationForest on *X* (list of feature vectors)."""
        if not _SKLEARN_AVAILABLE or self._model is None:
            return
        arr = np.array(X)
        if len(arr) < _MIN_SAMPLES_FOR_IF:
            _log.debug("Insufficient data for IsolationForest fit (%d samples)", len(arr))
            return
        self._model.fit(arr)
        self._training_data = [list(row) for row in arr]
        self._trained = True

    def score(self, x: list[float]) -> float:
        """Return anomaly score for feature vector *x*.

        Lower (more negative) scores indicate stronger anomalies.
        Returns 0.0 when the model has not been trained yet.
        """
        if self._trained and _SKLEARN_AVAILABLE and self._model is not None:
            return float(self._model.decision_function([x])[0])
        # Z-score fallback: use stored training data
        if len(self._training_data) >= 2:
            arr = np.array(self._training_data)
            means = arr.mean(axis=0)
            stds = arr.std(axis=0)
            stds = np.where(stds == 0, 1.0, stds)
            z = np.abs((np.array(x) - means) / stds).max()
            # Convert to IF-like scale: high z → more negative score
            return float(1.0 - z / _Z_SCORE_THRESHOLD)
        return 0.0

    def add_training_sample(self, x: list[float]) -> None:
        """Append a single feature vector to the training window."""
        self._training_data.append(x)

    def is_anomaly(self, x: list[float], threshold: float = _IF_THRESHOLD) -> bool:
        """Return True if *x* is anomalous (score < *threshold*)."""
        return self.score(x) < threshold
