"""Tests for core.system.phase_controller and resource_allocator."""
import pytest
from core.system.phase_controller import Phase, PhaseController
from core.system.resource_allocator import ResourceAllocator


def _fresh():
    return PhaseController()


def test_initial_phase():
    pc = _fresh()
    assert pc.current == Phase.RESEARCH


def test_tick_stays_in_research_with_few_signals():
    pc = _fresh()
    for _ in range(15):
        pc.tick({"avg_roas": 1.5, "win_rate": 0.6, "capital": 1000, "signal_count": 5})
    assert pc.current == Phase.RESEARCH


def test_promotes_to_explore_with_enough_signals():
    pc = _fresh()
    for _ in range(12):
        pc.tick({"avg_roas": 1.5, "win_rate": 0.6, "capital": 1000, "signal_count": 25})
    assert pc.current == Phase.EXPLORE


def test_promotes_explore_to_validate():
    pc = _fresh()
    pc.force_phase(Phase.EXPLORE)
    for _ in range(12):
        pc.tick({"avg_roas": 1.5, "win_rate": 0.6, "capital": 1000, "signal_count": 30})
    assert pc.current == Phase.VALIDATE


def test_promotes_validate_to_scale():
    pc = _fresh()
    pc.force_phase(Phase.VALIDATE)
    for _ in range(12):
        pc.tick({"avg_roas": 2.0, "win_rate": 0.5, "capital": 1000, "signal_count": 50})
    assert pc.current == Phase.SCALE


def test_drawdown_triggers_demotion():
    pc = _fresh()
    pc.force_phase(Phase.SCALE)
    pc.tick({"avg_roas": 2.0, "win_rate": 0.5, "capital": 2000, "signal_count": 50})
    # Simulate 30% drawdown
    pc.tick({"avg_roas": 1.0, "win_rate": 0.2, "capital": 1400, "signal_count": 50})
    assert pc.current == Phase.VALIDATE


def test_scale_no_demotion_within_threshold():
    pc = _fresh()
    pc.force_phase(Phase.SCALE)
    pc.tick({"avg_roas": 2.0, "win_rate": 0.5, "capital": 2000, "signal_count": 50})
    pc.tick({"avg_roas": 1.8, "win_rate": 0.4, "capital": 1600, "signal_count": 50})
    assert pc.current == Phase.SCALE


def test_status_shape():
    pc = _fresh()
    s = pc.status()
    assert "phase" in s
    assert "cycles_in_phase" in s
    assert "signal_count" in s


def test_record_signal_increments():
    pc = _fresh()
    pc.record_signal()
    pc.record_signal()
    assert pc.status()["signal_count"] == 2


# ── resource allocator ─────────────────────────────────────────────────────────

def test_budget_fractions_sum_to_one():
    ra = ResourceAllocator()
    for phase in Phase:
        fracs = ra.fractions(phase)
        assert abs(sum(fracs.values()) - 1.0) < 1e-9, phase


def test_budget_allocation_totals_correctly():
    ra = ResourceAllocator()
    alloc = ra.allocate_budget(Phase.SCALE, 1000.0)
    assert abs(sum(alloc.values()) - 1000.0) < 0.01


def test_workers_allocation_totals_correctly():
    ra = ResourceAllocator()
    for phase in Phase:
        workers = ra.allocate_workers(phase, total_workers=4)
        assert sum(workers.values()) == 4, phase


def test_describe_shape():
    ra = ResourceAllocator()
    desc = ra.describe(Phase.RESEARCH, 500.0)
    assert "phase" in desc
    assert "budget" in desc
    assert "workers" in desc
