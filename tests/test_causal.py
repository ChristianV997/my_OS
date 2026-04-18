from backend.causal.graph import CausalGraph
import backend.causal.update as causal_update
from backend.core.state import SystemState


def test_add_and_get_weight():
    g = CausalGraph()
    g.add_edge("revenue", "roas", 0.8)
    assert g.get_weight("revenue", "roas") == 0.8
    assert g.get_weight("missing", "roas") == 0.0


def test_children():
    g = CausalGraph()
    g.add_edge("cost", "roas", 0.5)
    g.add_edge("revenue", "roas", 0.8)
    assert "roas" in g.children("cost")
    assert "roas" in g.children("revenue")
    assert g.children("roas") == []


def test_parents():
    g = CausalGraph()
    g.add_edge("cost", "roas", 0.5)
    g.add_edge("revenue", "roas", 0.8)
    parents = g.parents("roas")
    assert "cost" in parents
    assert "revenue" in parents
    assert g.parents("cost") == []


def test_overwrite_edge():
    g = CausalGraph()
    g.add_edge("x", "y", 0.3)
    g.add_edge("x", "y", 0.9)
    assert g.get_weight("x", "y") == 0.9


def test_update_causal_fallback_stores_insights():
    state = SystemState()
    for i in range(20):
        state.event_log.log_batch([{
            "roas": 1.0 + (i * 0.01),
            "revenue": 100 + i,
            "cost": 50 + i,
            "variant": (i % 5) + 1,
            "intensity": 0.2 + (i * 0.01),
        }])

    orig = causal_update.DOWHY_AVAILABLE
    causal_update.DOWHY_AVAILABLE = False
    try:
        causal_update.update_causal(state.graph, state.event_log, state)
    finally:
        causal_update.DOWHY_AVAILABLE = orig

    assert "method" in state.causal_insights
