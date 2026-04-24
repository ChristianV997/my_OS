"""core.copilot.scenario — scenario runner for the copilot analysis layer.

Generates a set of spend-scaling scenarios around the current state so the
execution loop can evaluate which budget level maximises projected ROAS.
"""
from __future__ import annotations

from typing import Any

from core.copilot.whatif import what_if


# Budget multipliers to evaluate
_SCENARIOS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def run_scenarios(state: dict[str, Any]) -> dict[str, Any]:
    """Run a family of spend-scaling what-if scenarios.

    Returns a summary dict with the best scenario (highest projected ROAS)
    and all scenario projections.

    Parameters
    ----------
    state:
        Current campaign state.

    Returns
    -------
    dict with keys:
        ``best``       — projected state for the highest ROAS scenario
        ``scenarios``  — list of all projected states
        ``multiplier`` — spend multiplier of the best scenario
    """
    base_spend = state.get("spend", 0.0)
    results = []

    for mult in _SCENARIOS:
        new_spend = base_spend * mult
        projected = what_if(state, {"spend": new_spend, "budget": new_spend})
        projected["_multiplier"] = mult
        results.append(projected)

    best = max(results, key=lambda s: s.get("roas", 0.0))

    return {
        "best": best,
        "scenarios": results,
        "multiplier": best.get("_multiplier", 1.0),
    }
