"""core.copilot.whatif — what-if scenario simulation.

Applies a delta dict to a base state and returns the projected outcome.
"""
from __future__ import annotations

from typing import Any


def what_if(state: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Return a projected state by overlaying *delta* on *state*.

    All numeric fields in *delta* are treated as absolute overrides.
    The projected ROAS is estimated by scaling the base ``revenue`` by the
    ratio of new spend to old spend (spend-proportional linear model).

    Parameters
    ----------
    state:
        Base campaign / system state dict.
    delta:
        Proposed changes (e.g. ``{"budget": 1200.0}``).

    Returns
    -------
    dict
        Projected state with updated fields and estimated metrics.
    """
    projected = dict(state)
    projected.update(delta)

    # Estimate projected revenue using a linear spend model
    base_spend = state.get("spend", 0.0)
    new_spend = projected.get("spend", projected.get("budget", base_spend))
    base_revenue = state.get("revenue", 0.0)

    if base_spend > 0 and new_spend != base_spend:
        ratio = new_spend / base_spend
        projected["revenue"] = base_revenue * ratio
        projected["spend"] = new_spend

    # Recompute ROAS
    spend = projected.get("spend", 0.0)
    revenue = projected.get("revenue", 0.0)
    projected["roas"] = revenue / spend if spend > 0 else 0.0

    return projected
