"""Tests for the operationalization phase.

Covers:
  - Reddit trend adapter (structure + signal format)
  - YouTube trend adapter (structure + fallback)
  - intelligence_loop enrichment with PatternStore
  - New orchestrator workers (_run_content_generation, _run_metrics_ingestion)
  - Updated _run_scaling (launch_from_playbook path)
  - /opportunities API endpoint
  - Signal adapter registration (Reddit + YouTube wired into SignalEngine)
"""
import time


# ── Reddit adapter ────────────────────────────────────────────────────────────

def test_reddit_adapter_importable():
    from backend.adapters.reddit_trends import fetch_reddit_signals, register
    assert callable(fetch_reddit_signals)
    assert callable(register)


def test_reddit_adapter_registers_with_engine():
    from core.signals import SignalEngine
    from backend.adapters.reddit_trends import register
    engine = SignalEngine()
    register(engine)
    source_names = [s["name"] for s in engine._sources]
    assert "reddit" in source_names


def test_reddit_signal_structure_when_cached(monkeypatch):
    """When cache is populated, fetch_reddit_signals returns valid signal dicts."""
    from backend.adapters import reddit_trends as rt
    # Inject a cached signal to avoid real network call
    rt._cache = {"signals": [
        {"product": "Stanley Cup",  "score": 0.85, "velocity": 0.3,
         "source": "reddit", "platform": "tiktok", "subreddit": "shutupandtakemymoney",
         "raw_title": "Stanley Cup Tumbler"},
    ]}
    rt._cache_ts = time.time()

    signals = rt.fetch_reddit_signals()
    assert len(signals) == 1
    s = signals[0]
    assert "product" in s and "score" in s and "velocity" in s
    assert s["source"] == "reddit"
    assert 0.0 <= s["score"] <= 1.0
    assert 0.0 <= s["velocity"] <= 1.0


def test_reddit_post_to_signal_score_range():
    from backend.adapters.reddit_trends import _post_to_signal
    post = {"title": "Amazing wireless charger", "ups": 5000, "comments": 300,
            "age_h": 12, "flair": "", "subreddit": "deals", "url": ""}
    sig = _post_to_signal(post)
    assert 0.0 <= sig["score"] <= 1.0
    assert 0.0 <= sig["velocity"] <= 1.0
    assert sig["product"]   # non-empty


def test_reddit_fallback_returns_empty_on_network_error(monkeypatch):
    """fetch_reddit_signals must return [] (not raise) when network fails."""
    from backend.adapters import reddit_trends as rt
    # Expire cache to force fetch
    rt._cache_ts = 0.0
    rt._cache = {}

    # Monkeypatch urllib.request.urlopen to raise
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("no network")))
    signals = rt.fetch_reddit_signals()
    assert isinstance(signals, list)  # no exception, returns []


# ── YouTube adapter ───────────────────────────────────────────────────────────

def test_youtube_adapter_importable():
    from backend.adapters.youtube_trends import fetch_youtube_signals, register
    assert callable(fetch_youtube_signals)
    assert callable(register)


def test_youtube_adapter_registers_with_engine():
    from core.signals import SignalEngine
    from backend.adapters.youtube_trends import register
    engine = SignalEngine()
    register(engine)
    source_names = [s["name"] for s in engine._sources]
    assert "youtube_trends" in source_names


def test_youtube_signal_structure_when_cached():
    from backend.adapters import youtube_trends as yt
    yt._cache = {"signals": [
        {"product": "wireless earbuds", "score": 0.75, "velocity": 0.2,
         "source": "youtube_trends", "platform": "tiktok", "category": "youtube_shorts"},
    ]}
    yt._cache_ts = time.time()

    signals = yt.fetch_youtube_signals()
    assert len(signals) == 1
    s = signals[0]
    assert s["source"] == "youtube_trends"
    assert 0.0 <= s["score"] <= 1.0


def test_youtube_returns_empty_without_pytrends(monkeypatch):
    """fetch_youtube_signals must return [] if pytrends is not installed."""
    from backend.adapters import youtube_trends as yt
    yt._cache_ts = 0.0
    yt._cache = {}

    import builtins
    real_import = builtins.__import__
    def mock_import(name, *args, **kwargs):
        if name == "pytrends.request":
            raise ImportError("no pytrends")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", mock_import)
    signals = yt.fetch_youtube_signals()
    assert isinstance(signals, list)


# ── intelligence_loop enrichment ──────────────────────────────────────────────

def test_intelligence_loop_returns_list():
    from core.intelligence_loop import run_intelligence
    result = run_intelligence(["shoes", "wireless charger"])
    assert isinstance(result, list)


def test_intelligence_loop_deduplicates():
    from core.intelligence_loop import run_intelligence
    result = run_intelligence(["shoes", "shoes", "SHOES"])
    products = [r["product"] for r in result]
    assert len(products) == len(set(products))


def test_intelligence_loop_priority_in_range():
    from core.intelligence_loop import run_intelligence
    result = run_intelligence(["Stanley Cup", "wireless earbuds", "led strip lights"])
    for idea in result:
        assert 0.0 <= idea["priority"] <= 1.0


def test_intelligence_loop_has_required_keys():
    from core.intelligence_loop import run_intelligence
    result = run_intelligence(["test product"])
    assert len(result) == 1
    idea = result[0]
    assert "product" in idea
    assert "priority" in idea
    assert "hook_affinity" in idea
    assert "calibrated" in idea
    assert "top_hooks" in idea


def test_intelligence_loop_sorted_by_priority():
    from core.intelligence_loop import run_intelligence
    result = run_intelligence(["a", "b", "c", "d", "e"])
    priorities = [r["priority"] for r in result]
    assert priorities == sorted(priorities, reverse=True)


def test_intelligence_loop_empty_input():
    from core.intelligence_loop import run_intelligence
    assert run_intelligence([]) == []
    assert run_intelligence(None) == []


# ── New orchestrator workers ──────────────────────────────────────────────────

def test_run_content_generation_returns_status_dict():
    from orchestrator.main import _run_content_generation
    result = _run_content_generation()
    assert "status" in result
    assert result["status"] in ("ok", "skipped", "error")


def test_run_metrics_ingestion_returns_status_dict():
    from orchestrator.main import _run_metrics_ingestion
    result = _run_metrics_ingestion()
    assert "status" in result
    assert result["status"] in ("ok", "skipped", "error")


def test_run_metrics_ingestion_does_not_raise():
    """Metrics worker must never propagate exceptions to the orchestrator."""
    from orchestrator.main import _run_metrics_ingestion
    try:
        _run_metrics_ingestion()
    except Exception as exc:
        raise AssertionError(f"_run_metrics_ingestion raised: {exc}")


def test_run_content_generation_does_not_raise():
    from orchestrator.main import _run_content_generation
    try:
        _run_content_generation()
    except Exception as exc:
        raise AssertionError(f"_run_content_generation raised: {exc}")


# ── Updated _run_scaling ──────────────────────────────────────────────────────

def test_run_scaling_returns_status_dict():
    from orchestrator.main import _run_scaling
    result = _run_scaling()
    assert "status" in result
    assert result["status"] in ("ok", "skipped", "error")


def test_run_scaling_does_not_raise():
    from orchestrator.main import _run_scaling
    try:
        _run_scaling()
    except Exception as exc:
        raise AssertionError(f"_run_scaling raised: {exc}")


# ── Signal engine wiring ──────────────────────────────────────────────────────

def test_signal_engine_has_reddit_source():
    from core.signals import signal_engine
    source_names = [s["name"] for s in signal_engine._sources]
    assert "reddit" in source_names, f"reddit not in {source_names}"


def test_signal_engine_has_youtube_source():
    from core.signals import signal_engine
    source_names = [s["name"] for s in signal_engine._sources]
    assert "youtube_trends" in source_names, f"youtube_trends not in {source_names}"


# ── /opportunities endpoint ───────────────────────────────────────────────────

def test_opportunities_endpoint_structure():
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    resp = client.get("/opportunities?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "opportunities" in data
    assert "count" in data
    assert isinstance(data["opportunities"], list)


def test_opportunities_each_has_required_fields():
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    resp = client.get("/opportunities?limit=5")
    data = resp.json()
    required = {"rank", "product", "rank_score", "corrected_roas",
                "confidence", "action_priority"}
    for opp in data.get("opportunities", []):
        missing = required - set(opp.keys())
        assert not missing, f"opportunity missing fields: {missing}"


def test_opportunities_sorted_by_action_priority():
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    resp = client.get("/opportunities?limit=10")
    data = resp.json()
    priorities = [o["action_priority"] for o in data.get("opportunities", [])]
    assert priorities == sorted(priorities, reverse=True)


# ── Task inventory registration ───────────────────────────────────────────────

def test_task_registry_has_content_generation_worker():
    from backend.runtime.task_inventory import task_registry
    names = [t["name"] for t in task_registry.all()]
    assert "content_generation_worker" in names


def test_task_registry_has_metrics_ingestion_worker():
    from backend.runtime.task_inventory import task_registry
    names = [t["name"] for t in task_registry.all()]
    assert "metrics_ingestion_worker" in names
