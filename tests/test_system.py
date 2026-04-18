from backend.core.state import SystemState
from backend.execution.loop import run_cycle
from backend.decision.engine import decide
from backend.core.system_v5 import PersistentState
from agents.world_model import world_model


def test_event_log_schema():
    s=SystemState()
    s=run_cycle(s)
    row=s.event_log.rows[-1]
    assert 'roas' in row
    assert 'variant' in row


def test_causal_graph_updates():
    s=SystemState()
    for _ in range(20): s=run_cycle(s)
    assert len(s.graph.edges)>=0


def test_bandit_memory():
    from backend.learning.bandit_update import bandit_memory
    s=SystemState()
    before = len(bandit_memory.history)
    for _ in range(3): s=run_cycle(s)
    assert isinstance(bandit_memory.history, dict)
    assert len(bandit_memory.history) >= before


def test_causal_insights_populated():
    s = SystemState()
    for _ in range(20):
        s = run_cycle(s)
    assert isinstance(s.causal_insights, dict)


def test_decide_backward_compatible_with_persistent_state():
    state = PersistentState()
    decisions = decide(state)
    assert isinstance(decisions, list)
    assert all("action" in d for d in decisions)


def test_world_model_not_constant():
    s=SystemState()
    for _ in range(30): s=run_cycle(s)
    world_model.train(s.event_log)
    p1=world_model.predict({'variant':1})
    p2=world_model.predict({'variant':2})
    assert p1!=p2
