import numpy as np


class AnomalyDetector:
    """Z-score anomaly detector; flags values more than 3 std from the mean."""

    def __init__(self):
        self.history: list[float] = []

    def update(self, value: float) -> None:
        self.history.append(value)

    def is_anomaly(self, value: float) -> bool:
        if len(self.history) < 10:
            return False
        mean = np.mean(self.history)
        std = np.std(self.history)
        if std == 0:
            return value != mean
        return abs(value - mean) > 3 * std
