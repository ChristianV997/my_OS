"""core.engine.execution_loop — unified execution pipeline.

Step 53: Full System Wiring (core layer → RL + Copilot + Evolution)
Step 55: ML Anomaly Detection integrated as pre-flight check

Pipeline:
    RAW INPUT
     → DATA VALIDATION
     → ANOMALY DETECTION (auto-response if anomalous)
     → SCENARIO SIMULATION (copilot)
     → RL / POLICY DECISION
     → RISK ENFORCEMENT (final authority)
     → EXECUTION
     → STORE EXPERIENCE
"""
from __future__ import annotations

import logging
from typing import Any

from core.data.validator import validate_campaign
from core.copilot.scenario import run_scenarios
from core.copilot.optimizer import decide
from core.risk.guard import enforce
from core.rl.replay_buffer import ReplayBuffer
from core.rl.policy import PolicyNet
from core.anomaly.detector import detect
from core.anomaly.response import respond

_log = logging.getLogger(__name__)

buffer = ReplayBuffer()
_policy = PolicyNet()


def execution_step(raw_state: dict[str, Any]) -> dict[str, Any]:
    """Execute one cycle of the unified pipeline.

    Parameters
    ----------
    raw_state:
        Raw campaign / environment signal dict.

    Returns
    -------
    dict
        Result with keys ``action`` and ``state``.
    """
    # 1. VALIDATE
    record = validate_campaign(raw_state)
    state = record.dict()

    # 2. ANOMALY DETECTION (pre-flight check)
    if detect(state):
        auto_action = respond(state)
        if auto_action in ("KILL", "THROTTLE"):
            _log.warning("Anomaly detected — auto-response: %s", auto_action)
            buffer.add({"state": state, "action": auto_action, "reward": state.get("profit", 0.0)})
            return {"action": auto_action, "state": state}

    # 3. SIMULATION / COPILOT
    scenario = run_scenarios(state)

    # 4. RL / POLICY DECISION
    action = decide(scenario)

    # 5. RL policy can override (provides a second opinion)
    rl_action = _policy.select_action(state)
    # Prefer the copilot decision unless RL strongly disagrees (KILL override)
    if rl_action == "KILL" and action != "KILL":
        _log.debug("RL policy overrides copilot: KILL")
        action = "KILL"

    # 6. RISK ENFORCEMENT (FINAL AUTHORITY)
    action = enforce(action, state)

    # 7. EXECUTION (external call placeholder)
    result = {"action": action, "state": state}

    # 8. STORE EXPERIENCE
    exp = {
        "state": state,
        "action": action,
        "reward": state.get("profit", state.get("roas", 0.0)),
    }
    buffer.add(exp)

    return result
