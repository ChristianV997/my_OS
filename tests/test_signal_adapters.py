"""Tests for signal adapters (amazon_bestsellers, tiktok_organic)."""
import pytest
from unittest.mock import patch


def test_amazon_fetch_returns_mock_when_network_unavailable():
    from backend.adapters.amazon_bestsellers import fetch
    # Force a fresh cache miss with no network
    import backend.adapters.amazon_bestsellers as mod
    mod._CACHE = []
    mod._CACHE_TS = 0.0
    with patch("requests.get", side_effect=Exception("no network")):
        results = fetch()
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("product" in r for r in results)
    assert all("score" in r for r in results)


def test_amazon_fetch_cached():
    from backend.adapters.amazon_bestsellers import fetch
    import backend.adapters.amazon_bestsellers as mod
    import time
    sentinel = [{"product": "cached_item", "score": 0.9, "source": "test"}]
    mod._CACHE = sentinel
    mod._CACHE_TS = time.time()
    results = fetch()
    assert results is sentinel


def test_amazon_register():
    from backend.adapters.amazon_bestsellers import register
    from core.signals import SignalEngine
    engine = SignalEngine()
    register(engine)
    assert any(s["name"] == "amazon_bestsellers" for s in engine._sources)


def test_tiktok_fetch_returns_mock_when_no_credentials():
    import backend.adapters.tiktok_organic as mod
    mod._CACHE = []
    mod._CACHE_TS = 0.0
    mod._ACCESS_TOKEN = ""
    results = mod.fetch()
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("product" in r for r in results)
    assert all("score" in r for r in results)


def test_tiktok_register():
    from backend.adapters.tiktok_organic import register
    from core.signals import SignalEngine
    engine = SignalEngine()
    register(engine)
    assert any(s["name"] == "tiktok_organic" for s in engine._sources)


def test_signal_engine_with_adapters():
    from core.signals import SignalEngine
    import backend.adapters.amazon_bestsellers as amz_mod
    import backend.adapters.tiktok_organic as ttk_mod

    # Reset caches so fetch functions are called fresh
    amz_mod._CACHE = []
    amz_mod._CACHE_TS = 0.0
    ttk_mod._CACHE = []
    ttk_mod._CACHE_TS = 0.0

    amz_data = [{"product": "test_amz", "score": 0.8, "source": "amazon_bestsellers"}]
    ttk_data = [{"product": "test_ttk", "score": 0.9, "source": "tiktok_organic"}]

    engine = SignalEngine()
    engine.register_source("amazon_bestsellers", lambda: amz_data)
    engine.register_source("tiktok_organic",    lambda: ttk_data)

    signals = engine.get()
    assert len(signals) == 2
    sources = {s["source"] for s in signals}
    assert "amazon_bestsellers" in sources
    assert "tiktok_organic" in sources


def test_top_opportunities_ranked():
    from core.signals import SignalEngine
    engine = SignalEngine()
    signals = [
        {"product": "a", "score": 0.3},
        {"product": "b", "score": 0.9},
        {"product": "c", "score": 0.6},
    ]
    top = engine.top_opportunities(signals, n=2)
    assert top[0]["product"] == "b"
    assert top[1]["product"] == "c"
