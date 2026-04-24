from backend.core.regime_transition import detect_transition
from backend.core.state import SystemState
from backend.execution.loop import run_cycle


def test_detect_transition():
    assert detect_transition(None, None) is False
    assert detect_transition(None, "stable") is False
    assert detect_transition("stable", None) is True
    assert detect_transition("stable", "stable") is False
    assert detect_transition("unknown", "unknown") is False
    assert detect_transition("stable", "growth") is True


def test_run_cycle_tracks_transition_and_cooldown(monkeypatch):
    regimes = iter(["stable", "growth", "growth"])
    monkeypatch.setattr("backend.execution.loop.detector.detect", lambda _event_log, _macro=None: next(regimes))

    state = SystemState()
    assert state.detected_regime == "unknown"
    state = run_cycle(state)
    assert state.transition["occurred"] is True
    assert state.transition["from"] == "unknown"
    assert state.transition["to"] == "stable"
    assert state.transition_cooldown == 5

    state = run_cycle(state)
    assert state.transition["occurred"] is True
    assert state.transition["from"] == "stable"
    assert state.transition["to"] == "growth"
    assert state.transition_cooldown == 5

    state = run_cycle(state)
    assert state.transition["occurred"] is False
    assert state.transition["from"] == "growth"
    assert state.transition["to"] == "growth"
    assert state.transition_cooldown == 4
