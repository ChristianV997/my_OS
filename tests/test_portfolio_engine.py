"""Tests for backend/decision/portfolio_engine.py"""
from backend.decision.portfolio_engine import ingest_results, get_allocations, top_products
import core.portfolio as core_portfolio


def setup_function():
    """Reset shared portfolio state between tests."""
    core_portfolio.portfolio.clear()


def test_ingest_results_populates_portfolio():
    results = [
        {"action": {"variant": 1}, "revenue": 200.0, "cost": 100.0, "roas": 2.0},
        {"action": {"variant": 2}, "revenue": 150.0, "cost": 100.0, "roas": 1.5},
    ]
    ingest_results(results)
    allocs = get_allocations()
    assert "1" in allocs
    assert "2" in allocs


def test_allocations_sum_to_one():
    results = [
        {"action": {"variant": i}, "revenue": float(i * 50), "cost": 50.0, "roas": float(i)}
        for i in range(1, 5)
    ]
    ingest_results(results)
    allocs = get_allocations()
    total = sum(allocs.values())
    assert abs(total - 1.0) < 1e-6


def test_top_products_sorted_by_weight():
    results = [
        {"action": {"variant": 1}, "revenue": 300.0, "cost": 100.0, "roas": 3.0},
        {"action": {"variant": 2}, "revenue": 100.0, "cost": 100.0, "roas": 1.0},
    ]
    ingest_results(results)
    products = top_products(n=5)
    assert len(products) >= 2
    weights = [p["weight"] for p in products]
    assert weights == sorted(weights, reverse=True)


def test_top_products_empty_portfolio():
    products = top_products(n=5)
    assert isinstance(products, list)


def test_ingest_results_no_action_key():
    """Should not raise when action key is missing."""
    results = [{"revenue": 50.0, "cost": 25.0, "roas": 2.0}]
    ingest_results(results)  # should not raise
