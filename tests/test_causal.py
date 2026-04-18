from backend.causal.graph import CausalGraph


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
