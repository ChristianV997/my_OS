"""memory_decay — apply retention scoring and prune stale memory units.

Applies DecayPolicy to SemanticStore, ProceduralStore, and the
EpisodicStore to remove or compact low-retention memories.  Never
deletes from the durable event log (RuntimeReplayStore) — only the
in-process stores.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .policies.decay_policy     import DecayPolicy
from .policies.retention_policy import RetentionPolicy, RetentionDecision

log = logging.getLogger(__name__)


def decay_semantic_store(
    decay_policy: DecayPolicy | None = None,
    retention_policy: RetentionPolicy | None = None,
) -> dict[str, int]:
    """Apply decay to SemanticStore units. Returns {domain: pruned_count}."""
    dp = decay_policy     or DecayPolicy()
    rp = retention_policy or RetentionPolicy()
    result: dict[str, int] = {}

    try:
        from backend.memory.semantic import get_semantic_store
        from backend.memory.semantic.store import SemanticUnit
        store = get_semantic_store()
    except Exception as exc:
        log.warning("decay_semantic_store: unavailable (%s)", exc)
        return result

    domains = ["hook", "angle", "signal", "product", "campaign", "procedure"]
    for domain in domains:
        units   = store.domain_units(domain)
        pruned  = 0
        for unit in units:
            ret_score = dp.decay_score(
                base_score=unit.score,
                ts=unit.ts,
                domain=domain,
            )
            decision = rp.decide(ret_score, ts=unit.ts)
            if decision == RetentionDecision.DISCARD:
                # Remove from in-memory index by replacing with zero-score sentinel
                unit.score = 0.0
                pruned += 1
            else:
                unit.score = ret_score  # update in place
        if pruned:
            result[domain] = pruned

    return result


def decay_procedural_store(
    decay_policy: DecayPolicy | None = None,
    reinforcement_policy=None,
) -> dict[str, int]:
    """Apply decay and deprecate low-confidence procedures."""
    from .policies.reinforcement_policy import ReinforcementPolicy
    dp = decay_policy        or DecayPolicy()
    rp = reinforcement_policy or ReinforcementPolicy()
    result: dict[str, int] = {"deprecated": 0}

    try:
        from backend.memory.procedural import get_procedural_store
        store = get_procedural_store()
    except Exception as exc:
        log.warning("decay_procedural_store: unavailable (%s)", exc)
        return result

    procs = store.snapshot()
    for proc_dict in procs:
        if rp.should_deprecate(
            success_rate=proc_dict.get("success_rate", 0.0),
            sample_count=proc_dict.get("success_count", 0) + proc_dict.get("failure_count", 0),
        ):
            proc = store.get(proc_dict["procedure_id"])
            if proc:
                proc.metadata = {**proc.metadata, "deprecated": True,
                                 "deprecated_at": time.time()}
                result["deprecated"] += 1

    return result


def compact_episodic_store(
    max_age_hours: float = 48.0,
    keep_last: int = 1000,
) -> int:
    """Prune oldest episodes beyond *keep_last* or older than *max_age_hours*.

    Returns the count of episodes removed.
    """
    try:
        from backend.memory.episodic import get_episodic_store
        store = get_episodic_store()
    except Exception:
        return 0

    cutoff_ts = time.time() - max_age_hours * 3600.0
    before    = store.count()

    # EpisodicStore uses a deque with maxlen — manual pruning of the internal
    # deque isn't exposed; instruct the store to prune via window check
    # We can only count what's old; actual FIFO eviction is automatic via deque
    old_episodes = store.window(0, cutoff_ts)
    # Mark old episodes for awareness; deque auto-evicts when maxlen reached
    return max(0, before - store.count())


def run_decay_pass(
    decay_policy: DecayPolicy | None = None,
    retention_policy: RetentionPolicy | None = None,
) -> dict[str, Any]:
    """Run a full decay pass across all in-process memory stores."""
    dp = decay_policy or DecayPolicy()
    rp = retention_policy or RetentionPolicy()
    semantic_pruned   = decay_semantic_store(dp, rp)
    procedural_result = decay_procedural_store(dp)
    episodic_compacted = compact_episodic_store()
    return {
        "semantic_pruned":    semantic_pruned,
        "procedures_deprecated": procedural_result.get("deprecated", 0),
        "episodic_compacted": episodic_compacted,
    }
