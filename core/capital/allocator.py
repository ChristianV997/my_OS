"""core.capital.allocator — softmax-based capital allocation engine.

Step 54: Capital Allocation Curves

Implements the allocation strategy described in Step 54:

    score   = ROAS * 0.6 + profit * 0.3 - drawdown * 0.1
    budget_i = total_budget * softmax(score_i / temperature)

Hard limits:
    max_frac = 0.35  (35% of total budget per strategy)
    min_frac = 0.05  (5% minimum for active strategies)

Scaling curve:
    ROAS > 2.5  →  +30%
    ROAS > 2.0  →  +20%
    ROAS > 1.5  →  +10%
    ROAS < 1.0  →  -30%
    ROAS < 0.8  →  kill (0%)
"""
from __future__ import annotations

import math
from typing import Any


# Allocation limits
_MIN_FRAC = 0.05
_MAX_FRAC = 0.35


def _compute_score(strategy: dict[str, Any]) -> float:
    """Compute the composite score for a single strategy.

    score = ROAS * 0.6 + profit * 0.3 - drawdown * 0.1
    """
    roas = strategy.get("roas", 0.0)
    profit = strategy.get("profit", 0.0)
    drawdown = strategy.get("drawdown", 0.0)
    return roas * 0.6 + profit * 0.3 - drawdown * 0.1


def _softmax(scores: list[float], temperature: float) -> list[float]:
    """Return softmax probabilities for *scores*."""
    temp = max(temperature, 1e-8)
    exps = [math.exp(s / temp) for s in scores]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


def scale_budget(current_budget: float, roas: float) -> float:
    """Apply the ROAS-driven scaling curve to *current_budget*.

    Returns the adjusted budget (may be 0.0 if ROAS < 0.8 triggers a kill).
    """
    if roas > 2.5:
        return current_budget * 1.30
    if roas > 2.0:
        return current_budget * 1.20
    if roas > 1.5:
        return current_budget * 1.10
    if roas < 0.8:
        return 0.0   # kill
    if roas < 1.0:
        return current_budget * 0.70
    return current_budget


def allocate(
    strategies: list[dict[str, Any]],
    total_budget: float,
    temperature: float = 1.0,
) -> list[float]:
    """Allocate *total_budget* across *strategies* using softmax scoring.

    Parameters
    ----------
    strategies:
        List of strategy dicts; each should have keys ``roas``, ``profit``,
        ``drawdown`` (all default to 0.0 if missing).
    total_budget:
        Total capital to distribute.
    temperature:
        Softmax temperature.
        - 1.0 → balanced
        - 0.5 → aggressive (winner-takes-more)
        - 2.0 → conservative

    Returns
    -------
    list[float]
        Per-strategy budget allocations in the same order as *strategies*.
    """
    n = len(strategies)
    if n == 0:
        return []
    if n == 1:
        return [total_budget]

    raw_scores = [_compute_score(s) for s in strategies]
    weights = _softmax(raw_scores, temperature)

    allocations = [w * total_budget for w in weights]

    lo = _MIN_FRAC * total_budget
    hi = _MAX_FRAC * total_budget

    # Iteratively clamp to [lo, hi] and redistribute excess/deficit
    allocations = list(allocations)
    for _ in range(10):  # iterate until stable
        total = sum(allocations)
        if total == 0:
            break
        # Scale to total_budget
        allocations = [a * total_budget / total for a in allocations]
        # Clamp each to [lo, hi]
        allocations = [min(max(a, lo), hi) for a in allocations]

    return allocations
