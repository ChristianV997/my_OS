"""Backend portfolio engine — wraps core/portfolio.py for the execution loop.

Bridges the ``core.portfolio`` proportional allocator into the backend
budget system, enabling ROAS-weighted budget splits across concurrent
product pods / strategies.
"""
from core.portfolio import allocate_budget, update_portfolio

# Re-export the in-process portfolio dict from core (single source of truth)
from core.portfolio import portfolio  # noqa: F401


def ingest_results(results: list[dict]) -> None:
    """Feed a batch of execution results into the portfolio tracker.

    Each result dict should contain at minimum ``action``, ``revenue``,
    and ``cost`` keys (as produced by ``backend/execution/loop.py``).
    """
    for r in results:
        action = r.get("action", {})
        # Use variant as product identifier; fall back to a stringified action
        product_id = str(action.get("variant", action))
        update_portfolio(
            product_id,
            {
                "revenue": float(r.get("revenue", 0.0)),
                "spend": float(r.get("cost", 0.0)),
                "roas": float(r.get("roas", 0.0)),
            },
        )


def get_allocations() -> dict[str, float]:
    """Return the current proportional budget fractions per product/variant.

    Keys are product-id strings; values sum to ≤ 1.0.
    """
    from core.portfolio import portfolio as _portfolio
    return allocate_budget(_portfolio)


def top_products(n: int = 5) -> list[dict]:
    """Return the top-*n* products ranked by ROAS-derived allocation weight."""
    allocs = get_allocations()
    ranked = sorted(allocs.items(), key=lambda kv: kv[1], reverse=True)
    return [{"product_id": pid, "weight": round(w, 4)} for pid, w in ranked[:n]]
