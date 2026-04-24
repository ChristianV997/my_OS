"""core.copilot.integration — copilot analysis entry point."""
from __future__ import annotations

from typing import Any

from core.copilot.whatif import what_if


def copilot_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Return a copilot analysis for the given state.

    Runs a spend +20% what-if scenario and returns the projected outcome.
    """
    return {
        "scenario": what_if(state, {"budget": state.get("spend", 0.0) * 1.2}),
    }
