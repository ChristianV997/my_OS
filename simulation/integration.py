"""simulation.integration — orchestrator and API hooks for the simulation layer.

Provides ``_run_simulation()`` — a drop-in orchestrator worker that:
1. Warms up the scoring model from recent event history
2. Scores current signals
3. Records recent outcomes back into calibration (prediction-vs-reality)
4. Records predictions for the scored signals so outcomes can be matched later
5. Emits ``simulation.completed`` event via the canonical broker

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
    """Orchestrator worker: warm up, score signals, record recent outcomes."""
    try:
        from simulation.engine import simulation_engine as _engine
        from simulation.calibration import calibration_store
        from core.content.patterns import pattern_store
        from core.content.playbook import playbook_memory
        from core.signals import signal_engine as _sig_engine

        # ── pull context ──────────────────────────────────────────────────────
        try:
            patterns = pattern_store.get_patterns()
        except Exception:
            patterns = {}

        try:
            all_playbooks = {p.product: p for p in playbook_memory.all()}
        except Exception:
            all_playbooks = {}

        rows: list[dict] = []
        try:
            from backend.api import _state  # type: ignore[attr-defined]
            rows = list(_state.event_log.rows[-100:])
        except Exception:
            pass

        # ── warm up / retrain ─────────────────────────────────────────────────
        warm_ok = False
        if rows:
            warm_ok = _engine.warm_up(rows, patterns=patterns, playbooks=all_playbooks)

        # ── record outcomes into calibration audit trail ───────────────────────
        # For each recent row that has an actual ROAS, try to match a pending
        # prediction. Also call the engine's own calibration path.
        outcomes_recorded = 0
        for row in rows[-20:]:
            product = row.get("product", "")
            actual  = float(row.get("roas", 0.0) or 0.0)
            if not product or not actual:
                continue
            pred = float(row.get("predicted_roas", actual))
            # calibration audit store (prediction-vs-reality pairs)
            calibration_store.record(product, pred, actual, ts=row.get("ts"))
            # engine-level calibration (Bayesian bias corrector)
            _engine.record_outcome(product, pred, actual, event=row)
            outcomes_recorded += 1

        # ── score current signal candidates ───────────────────────────────────
        try:
            signals = _sig_engine.get()
        except Exception:
            signals = []

        ranked: list[Any] = []
        if signals:
            ranked = _engine.score_signals(
                signals,
                patterns=patterns,
                playbooks=all_playbooks,
            )

        # Stage predictions in calibration store so future outcomes can be paired
        for r in ranked:
            if r.product:
                calibration_store.record_prediction(r.product, r.predicted_roas)

        # ── emit simulation.completed event ───────────────────────────────────
        top_product = ranked[0].product if ranked else None
        scores_dicts = [r.to_dict() for r in ranked[:10]]
        try:
            from backend.events.emitter import emit_simulation_completed
            emit_simulation_completed(scores_dicts, top_product=top_product)
        except Exception:
            pass

        return {
            "status":           "ok",
            "warmed_up":        warm_ok,
            "signals_scored":   len(ranked),
            "outcomes_recorded": outcomes_recorded,
            "top_product":      top_product,
            "top_rank_score":   round(ranked[0].rank_score, 4) if ranked else None,
            "calibrated":       calibration_store.is_calibrated(),
        }

    except Exception as exc:
        _log.exception("simulation_worker_failed error=%s", exc)
        return {"status": "error", "error": str(exc)}
