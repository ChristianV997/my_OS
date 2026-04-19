from backend.core.system_v5 import PersistentState
from backend.execution.loop import run_cycle


def test_run_cycle_accepts_persistent_state(monkeypatch):
    monkeypatch.setattr("backend.execution.loop.get_orders", lambda **kw: [])
    monkeypatch.setattr(
        "backend.execution.loop.get_ad_spend",
        lambda **kw: {"campaigns": [], "total_spend": 0.0, "since": "", "until": ""},
    )

    state = PersistentState()
    updated = run_cycle(state)

    assert isinstance(updated, PersistentState)
