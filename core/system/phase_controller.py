"""core.system.phase_controller — manage the current execution phase."""
from __future__ import annotations

PHASES = ("RESEARCH", "EXPLORE", "EXPAND", "SCALE")


class PhaseController:
    """Track and transition the system execution phase.

    Phases follow the progression: RESEARCH → EXPLORE → EXPAND → SCALE.
    """

    def __init__(self, initial: str = "RESEARCH") -> None:
        if initial not in PHASES:
            raise ValueError(f"Unknown phase '{initial}'. Must be one of {PHASES}")
        self._phase = initial

    def set_phase(self, phase: str) -> None:
        """Set the current phase.

        Parameters
        ----------
        phase:
            One of ``"RESEARCH"``, ``"EXPLORE"``, ``"EXPAND"``, ``"SCALE"``.
        """
        if phase not in PHASES:
            raise ValueError(f"Unknown phase '{phase}'. Must be one of {PHASES}")
        self._phase = phase

    def get_phase(self) -> str:
        """Return the current phase name."""
        return self._phase

    def advance(self) -> str:
        """Advance to the next phase and return it.

        If already at the final phase, stays there.
        """
        idx = PHASES.index(self._phase)
        if idx < len(PHASES) - 1:
            self._phase = PHASES[idx + 1]
        return self._phase
