from __future__ import annotations


def score_confidence(
    confidence: float,
    *,
    consensus_score: float = 0.0,
    market_confidence: float = 0.0,
) -> float:
    base = min(1.0, max(0.0, float(confidence or 0.0)))
    consensus = min(1.0, max(0.0, float(consensus_score or 0.0)))
    market = min(1.0, max(0.0, float(market_confidence or 0.0)))
    score = (base * 0.55) + (consensus * 0.3) + (market * 0.15)
    return round(min(1.0, max(0.0, score)), 6)
