"""core.system.phase_controller — lifecycle phase management.

Phases advance in order:  RESEARCH → EXPLORE → VALIDATE → SCALE
Each phase has a minimum cycle count and a promotion condition based
on observed KPIs from the event log.

Promotion rules (conservative defaults, override via env vars):
  RESEARCH  → EXPLORE   when ≥ 20 signals collected
  EXPLORE   → VALIDATE  when avg_roas ≥ 1.2 over last 20 cycles
  VALIDATE  → SCALE     when avg_roas ≥ 1.8 AND win_rate ≥ 0.4
  SCALE stays until manually reset or a drawdown triggers demotion.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from enum import Enum
from typing import Any

_log = logging.getLogger(__name__)


class Phase(str, Enum):
    RESEARCH = "RESEARCH"
    EXPLORE  = "EXPLORE"
    VALIDATE = "VALIDATE"
    SCALE    = "SCALE"


_PHASE_ORDER = [Phase.RESEARCH, Phase.EXPLORE, Phase.VALIDATE, Phase.SCALE]

# Promotion thresholds — override via environment variables
_RESEARCH_MIN_SIGNALS  = int(os.getenv("PHASE_RESEARCH_MIN_SIGNALS", "20"))
_EXPLORE_MIN_ROAS      = float(os.getenv("PHASE_EXPLORE_MIN_ROAS", "1.2"))
_VALIDATE_MIN_ROAS     = float(os.getenv("PHASE_VALIDATE_MIN_ROAS", "1.8"))
_VALIDATE_MIN_WIN_RATE = float(os.getenv("PHASE_VALIDATE_MIN_WIN_RATE", "0.4"))
_MIN_CYCLES_PER_PHASE  = int(os.getenv("PHASE_MIN_CYCLES", "10"))

# Demotion: drop back one phase if drawdown exceeds this fraction
_MAX_DRAWDOWN_FRACTION = float(os.getenv("PHASE_MAX_DRAWDOWN", "0.25"))


class PhaseController:
    """Thread-safe phase lifecycle manager."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._phase = Phase.RESEARCH
        self._cycles_in_phase: int = 0
        self._entered_at: float = time.time()
        self._signal_count: int = 0
        self._peak_capital: float = 0.0

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def current(self) -> Phase:
        with self._lock:
            return self._phase

    def tick(self, metrics: dict[str, Any]) -> Phase:
        """Evaluate promotion/demotion given latest *metrics* and advance if ready.

        Parameters
        ----------
        metrics:
            Dict with keys: avg_roas, win_rate, capital, signal_count (optional).
        """
        with self._lock:
            self._cycles_in_phase += 1
            capital = float(metrics.get("capital", 0.0))
            if capital > self._peak_capital:
                self._peak_capital = capital

            # Update signal count if provided
            self._signal_count = int(metrics.get("signal_count", self._signal_count))

            # Check demotion first (drawdown guard)
            if self._peak_capital > 0:
                drawdown = (self._peak_capital - capital) / self._peak_capital
                if drawdown >= _MAX_DRAWDOWN_FRACTION and self._phase != Phase.RESEARCH:
                    self._demote()
                    return self._phase

            # Attempt promotion
            if self._cycles_in_phase >= _MIN_CYCLES_PER_PHASE:
                self._try_promote(metrics)

            return self._phase

    def record_signal(self) -> None:
        with self._lock:
            self._signal_count += 1

    def force_phase(self, phase: Phase) -> None:
        """Override phase (admin/testing use only)."""
        with self._lock:
            _log.warning("PhaseController: forced phase %s → %s", self._phase, phase)
            self._phase = phase
            self._cycles_in_phase = 0
            self._entered_at = time.time()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "phase":           self._phase.value,
                "cycles_in_phase": self._cycles_in_phase,
                "signal_count":    self._signal_count,
                "peak_capital":    round(self._peak_capital, 2),
                "entered_at":      self._entered_at,
            }

    # ── internal ──────────────────────────────────────────────────────────────

    def _try_promote(self, metrics: dict[str, Any]) -> None:
        avg_roas  = float(metrics.get("avg_roas", 0.0))
        win_rate  = float(metrics.get("win_rate",  0.0))

        if self._phase == Phase.RESEARCH and self._signal_count >= _RESEARCH_MIN_SIGNALS:
            self._advance()
        elif self._phase == Phase.EXPLORE and avg_roas >= _EXPLORE_MIN_ROAS:
            self._advance()
        elif (
            self._phase == Phase.VALIDATE
            and avg_roas  >= _VALIDATE_MIN_ROAS
            and win_rate  >= _VALIDATE_MIN_WIN_RATE
        ):
            self._advance()

    def _advance(self) -> None:
        idx = _PHASE_ORDER.index(self._phase)
        if idx < len(_PHASE_ORDER) - 1:
            old = self._phase
            self._phase = _PHASE_ORDER[idx + 1]
            self._cycles_in_phase = 0
            self._entered_at = time.time()
            _log.info("PhaseController: promoted %s → %s", old, self._phase)

    def _demote(self) -> None:
        idx = _PHASE_ORDER.index(self._phase)
        if idx > 0:
            old = self._phase
            self._phase = _PHASE_ORDER[idx - 1]
            self._cycles_in_phase = 0
            self._entered_at = time.time()
            _log.warning("PhaseController: drawdown demoted %s → %s", old, self._phase)


# Singleton
phase_controller = PhaseController()
