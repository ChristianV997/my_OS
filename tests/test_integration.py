from backend.core.state import SystemState
from backend.execution.loop import run_cycle


def test_run_5_cycles():
    state = SystemState()
    for _ in range(5):
        state = run_cycle(state)
    assert len(state.event_log.rows) > 0
    assert state.capital != 1000.0


def test_memory_populated():
    state = SystemState()
    for _ in range(3):
        state = run_cycle(state)
    assert len(state.memory) > 0


def test_memory_has_signals():
    state = SystemState()
    for _ in range(3):
        state = run_cycle(state)
    row = state.memory[-1]
    assert "velocity" in row
    assert "acceleration" in row
    assert "advantage" in row


def test_event_log_has_roas():
    state = SystemState()
    state = run_cycle(state)
    assert all("roas" in r for r in state.event_log.rows)


def test_event_log_capacity():
    from backend.data.event_log import EventLog
    log = EventLog()
    log.MAX_ROWS = 10
    for i in range(20):
        log.log_batch([{"roas": float(i)}])
    assert len(log.rows) <= 10
