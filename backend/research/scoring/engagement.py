from __future__ import annotations

from math import log1p


_SOURCE_WEIGHTS = {
    "reddit": 1.0,
    "hackernews": 1.1,
    "youtube": 1.2,
    "polymarket": 1.4,
}


def score_engagement(engagement: float, *, source: str = "reddit") -> float:
    weight = _SOURCE_WEIGHTS.get(source.strip().lower(), 1.0)
    normalized = max(0.0, float(engagement or 0.0))
    return round(log1p(normalized) * weight, 6)
