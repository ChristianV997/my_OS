from backend.core.state import SystemState
from backend.core.system_v5 import PersistentState
from backend.execution.loop import run_cycle


def test_persistent_state_is_system_state():
    state = PersistentState()
    assert isinstance(state, SystemState)
    assert hasattr(state, "event_log")
    assert hasattr(state, "graph")


def test_run_cycle_accepts_persistent_state():
    state = PersistentState()
    updated = run_cycle(state)
    assert isinstance(updated, PersistentState)
    assert len(updated.event_log.rows) > 0
