from core.signals import SignalEngine


def test_get_returns_mock_when_no_sources():
    engine = SignalEngine()
    signals = engine.get()
    assert isinstance(signals, list)
    assert len(signals) > 0
    assert all("product" in s for s in signals)
    assert all("score" in s for s in signals)


def test_get_uses_registered_source():
    engine = SignalEngine()

    def my_source():
        return [{"product": "super_widget", "score": 0.9}]

    engine.register_source("test", my_source)
    signals = engine.get()
    assert any(s["product"] == "super_widget" for s in signals)


def test_get_falls_back_on_source_error():
    engine = SignalEngine()

    def bad_source():
        raise RuntimeError("network error")

    engine.register_source("bad", bad_source)
    signals = engine.get()
    assert isinstance(signals, list)
    assert len(signals) > 0


def test_get_attaches_source_name():
    engine = SignalEngine()

    def my_source():
        return [{"product": "thing", "score": 0.7}]

    engine.register_source("mydata", my_source)
    signals = engine.get()
    thing = next(s for s in signals if s["product"] == "thing")
    assert thing["source"] == "mydata"


def test_filter_opportunities():
    engine = SignalEngine()
    signals = [
        {"product": "a", "score": 0.8},
        {"product": "b", "score": 0.3},
        {"product": "c", "score": 0.5},
    ]
    filtered = engine.filter_opportunities(signals, min_score=0.5)
    assert len(filtered) == 2
    assert all(s["score"] >= 0.5 for s in filtered)


def test_filter_opportunities_empty():
    engine = SignalEngine()
    assert engine.filter_opportunities([], min_score=0.5) == []


def test_top_opportunities():
    engine = SignalEngine()
    signals = [
        {"product": "a", "score": 0.2},
        {"product": "b", "score": 0.9},
        {"product": "c", "score": 0.6},
        {"product": "d", "score": 0.4},
    ]
    top = engine.top_opportunities(signals, n=2)
    assert len(top) == 2
    assert top[0]["product"] == "b"
    assert top[1]["product"] == "c"


def test_mock_signals_contain_platform_and_market():
    engine = SignalEngine()
    signals = engine._mock_signals()
    for s in signals:
        assert "market" in s
        assert "platform" in s
