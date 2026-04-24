"""core.risk.guard — lightweight risk-enforcement helper for the execution loop.

This wraps the GlobalRiskEngine so callers only need a single ``enforce()``
call that returns a cleaned action string.  If risk blocks the action the
result is overridden to "HOLD".
"""
from __future__ import annotations

from core.risk.global_risk_engine import GlobalRiskEngine

_engine = GlobalRiskEngine()


def enforce(action: str, state: dict) -> str:
    """Apply risk rules to a proposed action.

    If the global kill-switch is active, or the proposed spend would breach
    daily / drawdown limits, the action is overridden to "HOLD".

    Parameters
    ----------
    action:
        Proposed action string, e.g. "BUY", "SCALE", "KILL", "HOLD".
    state:
        Current campaign / system state dict.  Expected numeric keys:
        ``spend``, ``revenue``, ``profit``, ``drawdown``.

    Returns
    -------
    str
        Safe action — either the original *action* or "HOLD".
    """
    proposed_budget = state.get("spend", 0.0)
    current_capital = state.get("revenue", 0.0)
    peak_capital = max(current_capital, state.get("peak_capital", current_capital))
    today_spend = state.get("today_spend", proposed_budget)

    result = _engine.enforce(proposed_budget, current_capital, peak_capital, today_spend)
    if not result.allowed:
        return "HOLD"
    return action
