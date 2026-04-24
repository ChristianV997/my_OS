"""core.anomaly.response — auto-response engine for detected anomalies.

Step 55: ML Anomaly Detection + Auto-Response System

Standardised response actions:
    KILL      → terminate campaign (ROAS < 0.8)
    THROTTLE  → reduce budget -30% (ROAS < 1.2)
    NONE      → no action required
"""
from __future__ import annotations

from typing import Any


def respond(state: dict[str, Any]) -> str:
    """Return the appropriate defensive action for an anomalous *state*.

    Parameters
    ----------
    state:
        Campaign / system state dict.  Key used: ``roas``.

    Returns
    -------
    str
        One of ``"KILL"``, ``"THROTTLE"``, or ``"NONE"``.
    """
    roas = state.get("roas", 0.0)

    if roas < 0.8:
        return "KILL"

    if roas < 1.2:
        return "THROTTLE"

    return "NONE"
