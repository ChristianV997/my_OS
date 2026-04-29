"""procedural_reinforcement — extract and reinforce workflow procedures.

Reads ``decision.logged`` and ``campaign.launched`` events from a ReplayBatch,
extracts successful execution patterns, and either creates new Procedure
objects in ProceduralStore or reinforces existing ones with new ROAS outcomes.
"""
from __future__ import annotations

import logging
from typing import Any

from .schemas.replay_batch import ReplayBatch
from .policies.reinforcement_policy import ReinforcementPolicy

log = logging.getLogger(__name__)


def _proc_store():
    try:
        from backend.memory.procedural import get_procedural_store
        return get_procedural_store()
    except Exception:
        return None


def _extract_outcomes(batch: ReplayBatch) -> list[dict[str, Any]]:
    """Pull decision.logged and campaign.launched events with ROAS."""
    outcomes = []
    for ev in batch.events:
        ev_type = ev.get("type", "")
        if ev_type in ("decision.logged", "campaign.launched"):
            roas = float(ev.get("roas", ev.get("actual_roas", ev.get("estimated_roas", 0.0))))
            hook = ev.get("hook", "")
            if hook:
                outcomes.append({
                    "hook":    hook,
                    "angle":   ev.get("angle", ""),
                    "product": ev.get("product", ""),
                    "phase":   ev.get("phase", ""),
                    "roas":    roas,
                    "success": roas >= 1.0,
                })
    return outcomes


def _build_procedure_key(outcome: dict[str, Any]) -> str:
    return f"{outcome['product']}:{outcome['hook'][:40]}"


def reinforce_from_batch(
    batch: ReplayBatch,
    policy: ReinforcementPolicy | None = None,
) -> int:
    """Extract outcomes from *batch* and reinforce or create procedures.

    Returns the count of procedures reinforced or created.
    """
    policy = policy or ReinforcementPolicy()
    store  = _proc_store()
    if store is None:
        return 0

    outcomes  = _extract_outcomes(batch)
    count     = 0

    # Group by key (product:hook prefix)
    groups: dict[str, list[dict]] = {}
    for o in outcomes:
        groups.setdefault(_build_procedure_key(o), []).append(o)

    for key, group in groups.items():
        # Find existing procedure by name
        domain = "campaign"
        best_for = store.best_for_domain(domain, k=50)
        existing = next((p for p in best_for if p.name == key), None)

        if existing is None:
            # Create new procedure from group outcomes
            steps = [{"action": "launch", "hook": g["hook"],
                       "angle": g["angle"], "product": g["product"]}
                     for g in group[:3]]
            avg_roas = sum(g["roas"] for g in group) / len(group)
            store.create(name=key, domain=domain, steps=steps, avg_roas=avg_roas)
            count += 1
        else:
            # Reinforce existing procedure with new observations
            for g in group:
                store.record_outcome(
                    existing.procedure_id,
                    success=g["success"],
                    roas=g["roas"],
                )
            count += 1

    return count


def promote_high_confidence(policy: ReinforcementPolicy | None = None) -> list[str]:
    """Return procedure IDs that should be promoted to top-of-ranking."""
    policy = policy or ReinforcementPolicy()
    store  = _proc_store()
    if store is None:
        return []
    promoted = []
    for proc in store.snapshot():
        if policy.should_promote(
            success_rate=proc.get("success_rate", 0.0),
            sample_count=proc.get("success_count", 0) + proc.get("failure_count", 0),
            avg_roas=proc.get("avg_roas", 0.0),
        ):
            promoted.append(proc["procedure_id"])
    return promoted
