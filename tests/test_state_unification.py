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


def test_persistent_state_save_with_numpy(monkeypatch, tmp_path):
    import json
    import numpy as np
    import backend.core.system_v5 as system_v5

    state = system_v5.PersistentState()
    save_path = tmp_path / "system_state.json"
    monkeypatch.setattr(system_v5, "STATE_PATH", str(save_path))
    monkeypatch.setattr(system_v5.allocator, "weights", {"s": np.float64(0.8)})
    monkeypatch.setattr(system_v5.evolution_engine, "scores", {"s": np.float64(1.2)})

    state.memory = [{"score": np.float64(0.25), "nested": [np.float64(0.5)]}]
    state.energy = {"fatigue": np.float64(0.15), "load": np.float64(0.35)}
    state.population = [{"fitness": np.int64(3)}]
    state.event_log.rows = [{"roas": np.float64(1.7), "meta": {"x": np.float64(2.0)}}]

    state.save()

    with open(save_path, "r") as f:
        payload = json.load(f)

    assert payload["allocator_weights"]["s"] == 0.8
    assert payload["evolution_scores"]["s"] == 1.2
    assert payload["memory"][0]["score"] == 0.25
    assert payload["event_log_rows"][0]["meta"]["x"] == 2.0
