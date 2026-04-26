"""simulation.integration — orchestrator and API hooks for the simulation layer.

Provides ``_run_simulation()`` — a drop-in orchestrator worker that:
1. Warms up the scoring model from recent event history
2. Scores current signals
3. Records outcomes from the most recent completed cycle back into calibration

Also re-exports ``simulation_engine`` for use from ``backend/api.py``.
"""
from __future__ import annotations

import logging
import time
from typing import Any

_log = logging.getLogger(__name__)

# Re-export so api.py can do: from simulation.integration import simulation_engine
from simulation.engine import simulation_engine  # noqa: F401


def _run_simulation() -> dict[str, Any]:
    """Orchestrator worker: warm up, score signals, record recent outcomes.

    Returns a status dict compatible with the existing worker dispatch table.
    """
    try:
        from simulation.engine import simulation_engine as _engine
        from core.content.patterns import pattern_store
        from core.content.playbook import playbook_memory
        from core.signals import signal_engine as _sig_engine

        # Pull context
        try:
            patterns = pattern_store.get_patterns()
        except Exception:
            patterns = {}

        try:
            all_playbooks = {p.product: p for p in playbook_memory.all()}
        except Exception:
            all_playbooks = {}

        # Get recent event rows for warm-up and outcome recording
        rows: list[dict] = []
        try:
            from backend.api import _state  # type: ignore[attr-defined]
            rows = list(_state.event_log.rows[-100:])
        except Exception:
            pass

        # Warm up / retrain if we have data
        warm_ok = False
        if rows:
            warm_ok = _engine.warm_up(rows, patterns=patterns, playbooks=all_playbooks)

        # Record recent outcomes into calibration
        outcomes_recorded = 0
        for row in rows[-20:]:
            product = row.get("product", "")
            pred = row.get("predicted_roas", row.get("roas", 0.0))
            actual = row.get("roas", 0.0)
            if product and actual:
                _engine.record_outcome(product, float(pred), float(actual), event=row)
                outcomes_recorded += 1

        # Score current signal candidates
        try:
            signals = _sig_engine.get()
        except Exception:
            signals = []

        ranked = []
        if signals:
            ranked = _engine.score_signals(
                signals,
                patterns=patterns,
                playbooks=all_playbooks,
            )

        return {
            "status": "ok",
            "warmed_up": warm_ok,
            "signals_scored": len(ranked),
            "outcomes_recorded": outcomes_recorded,
            "top_product": ranked[0].product if ranked else None,
            "top_rank_score": round(ranked[0].rank_score, 4) if ranked else None,
        }

    except Exception as exc:
        _log.exception("simulation_worker_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}
