"""Tests for Step 74 — Content Feedback Loop, Pattern Extraction & Playbook."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# content.feedback
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_winner(self):
        from content.feedback import evaluate
        video = {"views": 15000, "likes": 900, "comments": 100}
        assert evaluate(video) == "WINNER"

    def test_loser(self):
        from content.feedback import evaluate
        video = {"views": 3000, "likes": 10, "comments": 5}
        assert evaluate(video) == "LOSER"

    def test_neutral(self):
        from content.feedback import evaluate
        # views >= 5000 but engagement <= 0.05
        video = {"views": 7000, "likes": 100, "comments": 50}
        assert evaluate(video) == "NEUTRAL"

    def test_zero_views_is_loser(self):
        from content.feedback import evaluate
        video = {"views": 0, "likes": 0, "comments": 0}
        assert evaluate(video) == "LOSER"

    def test_exact_threshold_winner(self):
        from content.feedback import evaluate
        # views > 10000 and engagement exactly > 0.05
        video = {"views": 10001, "likes": 501, "comments": 0}
        assert evaluate(video) == "WINNER"

    def test_boundary_neutral_not_winner(self):
        from content.feedback import evaluate
        # views > 10000 but engagement just below threshold
        video = {"views": 10001, "likes": 500, "comments": 0}
        assert evaluate(video) == "NEUTRAL"


# ---------------------------------------------------------------------------
# content.pattern_extractor
# ---------------------------------------------------------------------------

class TestExtractPattern:
    def test_full_video(self):
        from content.pattern_extractor import extract_pattern
        video = {
            "hook": "shock",
            "angle": "product demo",
            "format": "vertical",
            "pacing": "fast",
            "visual": "close-up",
            "views": 5000,
        }
        pattern = extract_pattern(video)
        assert pattern["hook"] == "shock"
        assert pattern["angle"] == "product demo"
        assert pattern["format"] == "vertical"
        assert pattern["pacing"] == "fast"
        assert pattern["visual"] == "close-up"

    def test_missing_fields_return_none(self):
        from content.pattern_extractor import extract_pattern
        pattern = extract_pattern({})
        assert pattern["hook"] is None
        assert pattern["angle"] is None
        assert pattern["format"] is None
        assert pattern["pacing"] is None
        assert pattern["visual"] is None

    def test_returns_only_pattern_keys(self):
        from content.pattern_extractor import extract_pattern
        pattern = extract_pattern({"hook": "x", "views": 99999})
        assert set(pattern.keys()) == {"hook", "angle", "format", "pacing", "visual"}


# ---------------------------------------------------------------------------
# content.memory
# ---------------------------------------------------------------------------

class TestMemory:
    def setup_method(self):
        from content import memory
        memory.clear()

    def test_store_and_retrieve(self):
        from content import memory
        from content.pattern_extractor import extract_pattern
        pattern = extract_pattern({"hook": "drama", "angle": "compare"})
        memory.store(pattern, "WINNER")
        all_mem = memory.get_all()
        assert len(all_mem) == 1
        assert all_mem[0]["result"] == "WINNER"
        assert all_mem[0]["hook"] == "drama"

    def test_accumulates(self):
        from content import memory
        memory.store({"hook": "a"}, "WINNER")
        memory.store({"hook": "b"}, "LOSER")
        assert len(memory.get_all()) == 2

    def test_clear(self):
        from content import memory
        memory.store({"hook": "x"}, "NEUTRAL")
        memory.clear()
        assert memory.get_all() == []

    def test_get_all_returns_copy(self):
        from content import memory
        memory.store({"hook": "y"}, "WINNER")
        copy = memory.get_all()
        copy.append({"hook": "z"})
        assert len(memory.get_all()) == 1


# ---------------------------------------------------------------------------
# content.playbook
# ---------------------------------------------------------------------------

class TestGeneratePlaybook:
    def test_no_winners_returns_none(self):
        from content.playbook import generate_playbook
        assert generate_playbook([]) is None
        assert generate_playbook([{"result": "LOSER", "hook": "x"}]) is None

    def test_playbook_from_winner(self):
        from content.playbook import generate_playbook
        mem = [{"result": "WINNER", "hook": "shock", "angle": "demo", "format": "vertical"}]
        pb = generate_playbook(mem)
        assert pb is not None
        assert pb["hook"] == "shock"
        assert pb["angle"] == "demo"
        assert pb["format"] == "vertical"
        assert "rules" in pb
        assert isinstance(pb["rules"], list)
        assert len(pb["rules"]) > 0

    def test_uses_first_winner(self):
        from content.playbook import generate_playbook
        mem = [
            {"result": "LOSER", "hook": "skip"},
            {"result": "WINNER", "hook": "first_win"},
            {"result": "WINNER", "hook": "second_win"},
        ]
        pb = generate_playbook(mem)
        assert pb["hook"] == "first_win"

    def test_rules_content(self):
        from content.playbook import generate_playbook
        mem = [{"result": "WINNER", "hook": "x", "angle": "y", "format": "z"}]
        pb = generate_playbook(mem)
        assert "fast cuts" in pb["rules"]


# ---------------------------------------------------------------------------
# content.pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    def setup_method(self):
        from content import memory
        memory.clear()

    def test_run_winner(self):
        from content.pipeline import run
        video = {
            "views": 20000, "likes": 1200, "comments": 200,
            "hook": "shock", "angle": "demo", "format": "vertical",
            "pacing": "fast", "visual": "close-up",
        }
        result = run(video)
        assert result["result"] == "WINNER"
        assert result["pattern"]["hook"] == "shock"
        assert result["playbook"] is not None

    def test_run_loser(self):
        from content.pipeline import run
        video = {"views": 100, "likes": 1, "comments": 0}
        result = run(video)
        assert result["result"] == "LOSER"
        assert result["playbook"] is None

    def test_run_batch(self):
        from content.pipeline import run_batch
        videos = [
            {"views": 20000, "likes": 1500, "comments": 200, "hook": "h1", "angle": "a1", "format": "f1"},
            {"views": 500,   "likes": 5,    "comments": 1,   "hook": "h2", "angle": "a2", "format": "f2"},
        ]
        results = run_batch(videos)
        assert len(results) == 2
        assert results[0]["result"] == "WINNER"
        assert results[1]["result"] == "LOSER"

    def test_memory_accumulates_across_runs(self):
        from content import memory
        from content.pipeline import run
        run({"views": 20000, "likes": 1500, "comments": 200})
        run({"views": 500,   "likes": 5,    "comments": 1})
        assert len(memory.get_all()) == 2

    def test_playbook_populated_after_winner(self):
        from content.pipeline import run
        run({"views": 500, "likes": 1, "comments": 0, "hook": "x"})
        result = run({"views": 20000, "likes": 2000, "comments": 500, "hook": "winner_hook"})
        assert result["playbook"] is not None
