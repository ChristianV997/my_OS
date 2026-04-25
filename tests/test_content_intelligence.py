"""Tests for core.content — feedback, patterns, and playbook modules."""
import pytest
from unittest.mock import patch, MagicMock


# ── classify_video ─────────────────────────────────────────────────────────────

def test_classify_video_winner():
    from core.content.feedback import classify_video
    result = classify_video({"roas": 2.0, "ctr": 0.03, "cvr": 0.02})
    assert result == "WINNER"


def test_classify_video_loser():
    from core.content.feedback import classify_video
    result = classify_video({"roas": 0.5, "ctr": 0.004, "cvr": 0.001})
    assert result == "LOSER"


def test_classify_video_neutral():
    from core.content.feedback import classify_video
    result = classify_video({"roas": 1.2, "ctr": 0.015, "cvr": 0.01})
    assert result == "NEUTRAL"


def test_classify_video_winner_via_cvr_only():
    from core.content.feedback import classify_video
    # High roas + high cvr but low ctr → still WINNER
    result = classify_video({"roas": 1.6, "ctr": 0.005, "cvr": 0.02})
    assert result == "WINNER"


# ── batch_classify ─────────────────────────────────────────────────────────────

def test_batch_classify_annotates_all():
    from core.content.feedback import batch_classify
    events = [
        {"roas": 2.0, "ctr": 0.03, "cvr": 0.02, "hook": "Hook A", "angle": "Angle X"},
        {"roas": 0.4, "ctr": 0.003, "cvr": 0.001},
        {"roas": 1.1, "ctr": 0.01, "cvr": 0.005},
    ]
    results = batch_classify(events)
    assert len(results) == 3
    for r in results:
        assert "label" in r
        assert "eng_score" in r
        assert r["label"] in ("WINNER", "LOSER", "NEUTRAL")


def test_batch_classify_does_not_mutate_originals():
    from core.content.feedback import batch_classify
    events = [{"roas": 2.0, "ctr": 0.03, "cvr": 0.02}]
    batch_classify(events)
    assert "label" not in events[0]


def test_batch_classify_stores_winners_in_memory():
    from core.content.feedback import batch_classify
    winner = {"roas": 2.0, "ctr": 0.03, "cvr": 0.02, "hook": "Hook A", "angle": "Great angle"}
    loser  = {"roas": 0.3, "ctr": 0.002, "cvr": 0.001}

    stored = []
    fake_cm = MagicMock()
    fake_cm.add.side_effect = lambda emb, meta: stored.append(meta)

    with patch("core.content.feedback._get_creative_memory", return_value=fake_cm):
        batch_classify([winner, loser])

    assert len(stored) == 1
    assert stored[0]["hook"] == "Hook A"


# ── extract_patterns ───────────────────────────────────────────────────────────

def test_extract_patterns_returns_required_keys():
    from core.content.patterns import extract_patterns
    events = [
        {"hook": "Hook A", "angle": "Angle X", "env_regime": "growth", "eng_score": 0.8},
        {"hook": "Hook B", "angle": "Angle Y", "env_regime": "decay",  "eng_score": 0.3},
        {"hook": "Hook A", "angle": "Angle X", "env_regime": "growth", "eng_score": 0.9},
    ]
    p = extract_patterns(events)
    assert "hook_scores" in p
    assert "angle_scores" in p
    assert "top_hooks" in p
    assert "top_angles" in p


def test_extract_patterns_ranks_correctly():
    from core.content.patterns import extract_patterns
    events = [
        {"hook": "Low Hook",  "eng_score": 0.2},
        {"hook": "High Hook", "eng_score": 0.9},
        {"hook": "Mid Hook",  "eng_score": 0.5},
    ]
    p = extract_patterns(events)
    assert p["top_hooks"][0] == "High Hook"


# ── PatternStore ───────────────────────────────────────────────────────────────

def test_pattern_store_update_and_top_hooks():
    from core.content.patterns import PatternStore
    ps = PatternStore()
    ps.update({"hook_scores": {"Hook A": 0.9, "Hook B": 0.4}, "angle_scores": {}, "regime_scores": {}})
    top = ps.get_top_hooks(n=1)
    assert top == ["Hook A"]


# ── generate_playbook + PlaybookMemory ─────────────────────────────────────────

def test_generate_playbook_shape():
    from core.content.playbook import generate_playbook
    events = [
        {"hook": "Hook A", "angle": "Angle X", "roas": 2.0, "eng_score": 0.8},
        {"hook": "Hook B", "angle": "Angle Y", "roas": 1.8, "eng_score": 0.7},
    ]
    pb = generate_playbook("ProductX", events, phase="VALIDATE")
    assert pb.product == "ProductX"
    assert pb.phase == "VALIDATE"
    assert len(pb.top_hooks) > 0
    assert pb.estimated_roas > 0
    assert 0 < pb.confidence <= 1


def test_playbook_memory_upsert_and_get():
    from core.content.playbook import PlaybookMemory, Playbook
    mem = PlaybookMemory()
    pb = Playbook(
        product="Widget",
        phase="SCALE",
        top_hooks=["Hook A"],
        top_angles=["Direct"],
        estimated_roas=2.5,
        confidence=0.4,
        evidence_count=4,
    )
    mem.upsert(pb)
    retrieved = mem.get("Widget", "SCALE")
    assert retrieved is not None
    assert retrieved.product == "Widget"
    assert retrieved.top_hooks == ["Hook A"]


# ── orchestrator worker integration ────────────────────────────────────────────

def test_run_feedback_collection_ok():
    from orchestrator.main import _run_feedback_collection
    fake_state = MagicMock()
    fake_state.event_log.rows = [
        {"roas": 2.0, "ctr": 0.03, "cvr": 0.02, "hook": "Hook A",
         "angle": "Angle X", "product": "TestProd", "env_regime": "growth"},
        {"roas": 0.4, "ctr": 0.003, "cvr": 0.001, "product": "TestProd"},
    ]
    with patch("backend.api._state", fake_state):
        result = _run_feedback_collection()
    assert result["status"] == "ok"
    assert result["classified"] == 2
    assert result["winners"] >= 1


def test_run_feedback_collection_skips_when_no_rows():
    from orchestrator.main import _run_feedback_collection
    fake_state = MagicMock()
    fake_state.event_log.rows = []
    with patch("backend.api._state", fake_state):
        result = _run_feedback_collection()
    assert result["status"] == "skipped"
