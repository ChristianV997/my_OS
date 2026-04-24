"""core.copilot.optimizer — decide the best action from scenario outputs."""
from __future__ import annotations

from typing import Any


def decide(scenario_result: dict[str, Any]) -> str:
    """Return a recommended action based on the best scenario.

    Parameters
    ----------
    scenario_result:
        Output of ``core.copilot.scenario.run_scenarios()``.

    Returns
    -------
    str
        Action string: "SCALE", "HOLD", "KILL", or "BUY".
    """
    best = scenario_result.get("best", {})
    roas = best.get("roas", 0.0)
    multiplier = scenario_result.get("multiplier", 1.0)

    if roas >= 2.0 and multiplier > 1.0:
        return "SCALE"
    if roas < 0.8:
        return "KILL"
    if roas < 1.0:
        return "HOLD"
    return "BUY"
