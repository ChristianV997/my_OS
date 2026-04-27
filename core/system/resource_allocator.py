"""core.system.resource_allocator — phase-aware budget & worker allocation.

Maps the current Phase to fractional resource allocations so the
orchestrator can distribute budget and worker slots appropriately.

Fractions represent how much of the TOTAL available resource goes to
each activity.  They always sum to 1.0 within a phase.
"""
from __future__ import annotations

from typing import Any

from core.system.phase_controller import Phase


# Phase → resource fractions
# Keys: research, signal_ingestion, exploration, validation, scaling, risk_reserve
_PHASE_ALLOCATIONS: dict[Phase, dict[str, float]] = {
    Phase.RESEARCH: {
        "research":        0.60,
        "signal_ingestion":0.25,
        "exploration":     0.10,
        "validation":      0.00,
        "scaling":         0.00,
        "risk_reserve":    0.05,
    },
    Phase.EXPLORE: {
        "research":        0.20,
        "signal_ingestion":0.15,
        "exploration":     0.45,
        "validation":      0.10,
        "scaling":         0.00,
        "risk_reserve":    0.10,
    },
    Phase.VALIDATE: {
        "research":        0.10,
        "signal_ingestion":0.10,
        "exploration":     0.20,
        "validation":      0.45,
        "scaling":         0.05,
        "risk_reserve":    0.10,
    },
    Phase.SCALE: {
        "research":        0.05,
        "signal_ingestion":0.05,
        "exploration":     0.10,
        "validation":      0.15,
        "scaling":         0.55,
        "risk_reserve":    0.10,
    },
}

# Default worker slot counts per phase (for a 4-worker pool)
_PHASE_WORKERS: dict[Phase, dict[str, int]] = {
    Phase.RESEARCH:  {"research": 2, "execution": 1, "scaling": 0, "reserved": 1},
    Phase.EXPLORE:   {"research": 1, "execution": 2, "scaling": 0, "reserved": 1},
    Phase.VALIDATE:  {"research": 1, "execution": 1, "scaling": 1, "reserved": 1},
    Phase.SCALE:     {"research": 0, "execution": 1, "scaling": 2, "reserved": 1},
}


class ResourceAllocator:
    """Computes concrete resource amounts from phase fractions."""

    def allocate_budget(self, phase: Phase, total_budget: float) -> dict[str, float]:
        """Return dollar amounts for each activity given *total_budget*."""
        fractions = _PHASE_ALLOCATIONS[phase]
        return {k: round(v * total_budget, 2) for k, v in fractions.items()}

    def allocate_workers(self, phase: Phase, total_workers: int = 4) -> dict[str, int]:
        """Return worker slot counts scaled to *total_workers*."""
        base = _PHASE_WORKERS[phase]
        base_total = sum(base.values())
        if base_total == 0:
            return {k: 0 for k in base}
        scale = total_workers / base_total
        result = {k: max(0, round(v * scale)) for k, v in base.items()}
        # Ensure exact total by adjusting "reserved"
        diff = total_workers - sum(result.values())
        result["reserved"] = max(0, result.get("reserved", 0) + diff)
        return result

    def fractions(self, phase: Phase) -> dict[str, float]:
        """Raw fractions for a phase (always sum to 1.0)."""
        return dict(_PHASE_ALLOCATIONS[phase])

    def describe(self, phase: Phase, total_budget: float = 500.0) -> dict[str, Any]:
        return {
            "phase":   phase.value,
            "budget":  self.allocate_budget(phase, total_budget),
            "workers": self.allocate_workers(phase),
        }


# Singleton
resource_allocator = ResourceAllocator()
