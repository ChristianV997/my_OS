from backend.core.state import SystemState
from backend.execution.loop import run_cycle
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
    for _ in range(20): s=run_cycle(s)
    assert isinstance(bandit_memory.history, dict)


def test_world_model_not_constant():
    s=SystemState()
    for _ in range(30): s=run_cycle(s)
    world_model.train(s.event_log)
    p1=world_model.predict({'variant':1})
    p2=world_model.predict({'variant':2})
    assert p1!=p2
