"""simulation.engine — SimulationEngine orchestrator.

Main entry point for the simulation layer.  Sits between discovery and
execution: given a list of signal candidates it scores them, corrects for
calibration bias, ranks them, and returns ordered SimulationResults.

Lifecycle
---------
1. ``warm_up(rows)`` — train the scoring model on existing event history
2. ``score_signals(signals, ...)`` — score + rank candidates pre-execution
3. ``record_outcome(...)`` — feed actual outcomes back to the calibrator

All state is held in process-local singletons (scoring_model, replay_store,
simulation_calibrator) — no external dependencies required at import time.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

_log = logging.getLogger(__name__)


class SimulationEngine:
    """Orchestrates feature extraction, scoring, ranking, and calibration.

    Thread-safe: all public methods acquire ``_lock`` where needed.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._warmed_up = False
        self._last_train_ts: float | None = None
        self._score_count = 0
        self._outcome_count = 0

    # ------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------

    def warm_up(
        self,
        rows: list[dict],
        patterns: dict | None = None,
        playbooks: dict | None = None,
        force: bool = False,
    ) -> bool:
        """Train the scoring model on historical event rows.

        Called at startup and periodically when new data arrives.
        Returns True if training succeeded.
        """
        from simulation.model import scoring_model
        from simulation.replay import replay_store

        # Ingest into replay store
        replay_store.ingest(rows)

        # Retrain scoring model
        ok = scoring_model.fit(rows, patterns=patterns, playbooks=playbooks)
        if ok:
            with self._lock:
                self._warmed_up = True
                self._last_train_ts = time.time()
            _log.info("simulation_warmed_up rows=%d", len(rows))
        return ok

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_signals(
        self,
        signals: list[dict],
        patterns: dict | None = None,
        playbooks: dict | None = None,
        history_map: dict[str, list[dict]] | None = None,
    ) -> list[Any]:  # list[SimulationResult]
        """Score and rank a list of signal candidates.

        Returns an ordered list of SimulationResult (rank 1 = best).
        """
        from simulation.calibrator import simulation_calibrator
        from simulation.model import scoring_model
        from simulation.ranking import build_result, rank_results
        from simulation.replay import replay_store

        if not signals:
            return []

        # Fill history from replay store if not provided
        if history_map is None:
            products = {s.get("product", "") for s in signals}
            history_map = {
                p: replay_store.product_history(p, limit=50)
                for p in products if p
            }

        scores = scoring_model.predict(
            signals,
            patterns=patterns,
            playbooks=playbooks,
            history_map=history_map,
        )

        results = []
        for sig, eng in zip(signals, scores):
            product = sig.get("product", "")
            hist = (history_map or {}).get(product, [])
            r = build_result(
                sig, eng,
                history=hist,
                patterns=patterns,
                calibrator=simulation_calibrator,
            )
            results.append(r)

        ranked = rank_results(results)

        with self._lock:
            self._score_count += len(ranked)

        return ranked

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        product: str,
        predicted_roas: float,
        actual_roas: float,
        event: dict | None = None,
    ) -> None:
        """Feed one (predicted, actual) pair into the calibration loop.

        Also ingests the full event dict into the replay store.
        """
        from simulation.calibrator import simulation_calibrator
        from simulation.replay import replay_store

        simulation_calibrator.record(product, predicted_roas, actual_roas)

        if event:
            replay_store.ingest([event])

        with self._lock:
            self._outcome_count += 1

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report(self) -> dict:
        """Return a snapshot of simulation layer health and stats."""
        from simulation.calibrator import simulation_calibrator
        from simulation.model import scoring_model
        from simulation.replay import replay_store

        with self._lock:
            warmed = self._warmed_up
            score_count = self._score_count
            outcome_count = self._outcome_count
            last_train = self._last_train_ts

        return {
            "warmed_up": warmed,
            "score_count": score_count,
            "outcome_count": outcome_count,
            "last_train_ts": last_train,
            "model": scoring_model.info(),
            "calibration": simulation_calibrator.report(),
            "replay_rows": replay_store.row_count(),
            "ts": time.time(),
        }

    def top_hooks(self, n: int = 5) -> list[dict]:
        from simulation.replay import replay_store
        return replay_store.hook_stats(top_n=n)

    def top_angles(self, n: int = 5) -> list[dict]:
        from simulation.replay import replay_store
        return replay_store.angle_stats(top_n=n)


# module-level singleton
simulation_engine = SimulationEngine()
