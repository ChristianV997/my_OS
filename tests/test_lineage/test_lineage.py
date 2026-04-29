"""Tests for the causal worldline graph and lineage tracker."""
import pytest

from backend.lineage import (
    LineageNode, LineageGraph, Worldline, LineageTracker,
    inherit_lineage, stamp_artifact_lineage, extract_lineage_metadata,
    build_lineage_chain,
)
from backend.contracts import CampaignAsset, SimulationArtifact


# ── LineageNode ───────────────────────────────────────────────────────────────

def test_lineage_node_to_dict():
    n = LineageNode(node_id="n1", node_type="campaign", label="test")
    d = n.to_dict()
    assert d["node_id"] == "n1"
    assert d["node_type"] == "campaign"
    assert "ts" in d


def test_lineage_node_from_dict():
    n = LineageNode(node_id="n2", node_type="simulation")
    d = n.to_dict()
    n2 = LineageNode.from_dict(d)
    assert n2.node_id == "n2"
    assert n2.node_type == "simulation"


# ── LineageGraph ──────────────────────────────────────────────────────────────

def test_graph_add_and_get():
    g = LineageGraph()
    n = LineageNode(node_id="g1", node_type="signal")
    g.add_node(n)
    assert g.get("g1") is not None


def test_graph_ancestors():
    g = LineageGraph()
    root   = LineageNode(node_id="root", node_type="simulation")
    middle = LineageNode(node_id="mid",  node_type="campaign", parent_ids=["root"])
    leaf   = LineageNode(node_id="leaf", node_type="outcome",  parent_ids=["mid"])
    for node in [root, middle, leaf]:
        g.add_node(node)
    ancestors = g.ancestors("leaf")
    ancestor_ids = {a.node_id for a in ancestors}
    assert "mid"  in ancestor_ids
    assert "root" in ancestor_ids


def test_graph_descendants():
    g = LineageGraph()
    root  = LineageNode(node_id="root2",  node_type="simulation")
    child = LineageNode(node_id="child2", node_type="campaign", parent_ids=["root2"])
    g.add_node(root)
    g.add_node(child)
    descs = g.descendants("root2")
    assert any(d.node_id == "child2" for d in descs)


def test_graph_lineage_chain_includes_node():
    g    = LineageGraph()
    root = LineageNode(node_id="chain_root", node_type="sim")
    tip  = LineageNode(node_id="chain_tip",  node_type="cam", parent_ids=["chain_root"])
    g.add_node(root)
    g.add_node(tip)
    chain = g.lineage_chain("chain_tip")
    assert "chain_tip" in chain


def test_graph_nodes_by_type():
    g = LineageGraph()
    g.add_node(LineageNode(node_id="t1", node_type="signal"))
    g.add_node(LineageNode(node_id="t2", node_type="signal"))
    g.add_node(LineageNode(node_id="t3", node_type="campaign"))
    signals = g.nodes_by_type("signal")
    assert len(signals) == 2


def test_graph_count():
    g = LineageGraph()
    assert g.count() == 0
    g.add_node(LineageNode(node_id="x1", node_type="test"))
    assert g.count() == 1


# ── LineageTracker ────────────────────────────────────────────────────────────

def test_tracker_track_returns_id():
    t   = LineageTracker()
    nid = t.track(node_type="signal", label="test signal", source="test")
    assert isinstance(nid, str)
    assert len(nid) > 0


def test_tracker_track_artifact():
    t = LineageTracker()
    a = CampaignAsset(campaign_id="tracker-001", product="earbuds")
    t.track_artifact(a)
    node = t.graph().get(a.artifact_id)
    assert node is not None
    assert node.node_type == "campaign"


def test_tracker_worldline():
    t   = LineageTracker()
    wid = t.start_worldline(label="test worldline")
    nid = t.track(node_type="step", label="step1")
    t.append_to_worldline(wid, nid)
    t.terminate_worldline(wid)
    wl = t.get_worldline(wid)
    assert wl is not None
    assert wl.terminated_at > 0
    assert len(wl.steps) == 1


def test_tracker_node_count():
    t = LineageTracker()
    assert t.node_count() == 0
    t.track(node_type="test")
    assert t.node_count() == 1


def test_tracker_ancestors():
    t    = LineageTracker()
    pid  = t.track(node_type="simulation", label="parent")
    cid  = t.track(node_type="campaign",   label="child", parent_ids=[pid])
    ancs = t.ancestors(cid)
    assert any(a.node_id == pid for a in ancs)


# ── propagation helpers ───────────────────────────────────────────────────────

def test_inherit_lineage_deduplication():
    result = inherit_lineage(["p1", "p2"], extra_parents=["p2", "p3"])
    assert result.count("p2") == 1
    assert "p3" in result


def test_stamp_artifact_lineage():
    parent = SimulationArtifact(simulation_id="stamp-parent")
    child  = CampaignAsset(campaign_id="stamp-child")
    stamp_artifact_lineage(child, parent_artifact=parent)
    assert parent.artifact_id in child.parent_ids


def test_extract_lineage_metadata():
    a   = CampaignAsset(campaign_id="meta-001", parent_ids=["p1"])
    meta = extract_lineage_metadata(a)
    assert meta["artifact_id"] == a.artifact_id
    assert "p1" in meta["parent_ids"]


def test_build_lineage_chain():
    a = SimulationArtifact(simulation_id="chain-a")
    b = CampaignAsset(campaign_id="chain-b", parent_ids=[a.artifact_id])
    chain = build_lineage_chain([a, b])
    assert chain[0] == a.artifact_id
    assert chain[1] == b.artifact_id
