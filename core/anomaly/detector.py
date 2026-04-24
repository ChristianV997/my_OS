"""core.anomaly.detector — anomaly detection service.

Maintains a module-level AnomalyModel instance so state accumulates across
calls within the same process.
"""
from __future__ import annotations

from typing import Any

from core.anomaly.model import AnomalyModel
from core.anomaly.features import build_features

_model = AnomalyModel()


def detect(state: dict[str, Any]) -> bool:
    """Return True if the current *state* is anomalous.

    The model is opportunistically fitted whenever there is enough history.
    Each call also adds the current features to the training window so the
    model adapts over time.
    """
    x = build_features(state)

    # Accumulate training data via the public API and refit periodically
    _model.add_training_sample(x)
    _REFIT_INTERVAL = 50
    n = len(_model._training_data)
    if n >= 10 and n % _REFIT_INTERVAL == 0:
        _model.fit(_model._training_data[-500:])

    return _model.is_anomaly(x)
