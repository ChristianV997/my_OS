from __future__ import annotations

from math import log1p


def score_velocity(current_engagement: float, previous_engagement: float = 0.0, *, elapsed_hours: float = 1.0) -> float:
    elapsed = max(0.25, float(elapsed_hours or 1.0))
    current = max(0.0, float(current_engagement or 0.0))
    previous = max(0.0, float(previous_engagement or 0.0))
    delta = max(0.0, current - previous)
    return round(log1p(delta) / elapsed, 6)
