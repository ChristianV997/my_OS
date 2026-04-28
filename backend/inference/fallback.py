"""backend.inference.fallback — deterministic fallback scheduling utilities.

Provides helpers for building and evaluating fallback chains so the router
can use consistent ordering across all call sites.

The canonical fallback order (when no explicit override is provided) is:
  OpenAI → Ollama → AirLLM → vLLM → LiteLLM → Mock

All fallback events emit telemetry via telemetry.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.inference.models.inference_response import InferenceResponse

# Default fallback order — mirrors RoutingPolicy._DEFAULT_ORDER priority
DEFAULT_FALLBACK_ORDER = ["openai", "ollama", "airllm", "vllm", "litellm", "mock"]


def build_fallback_chain(
    primary: str,
    available: list[str] | None = None,
    order: list[str] | None = None,
) -> list[str]:
    """Return an ordered fallback chain starting after the primary provider.

    Parameters
    ----------
    primary : str
        The provider that will be tried first (excluded from the chain).
    available : list[str] | None
        Providers currently registered and healthy.  If None, uses ``order``.
    order : list[str] | None
        Priority order.  Defaults to DEFAULT_FALLBACK_ORDER.

    Returns
    -------
    list[str]
        Ordered list of fallback providers (not including primary).
    """
    _order = order or DEFAULT_FALLBACK_ORDER
    _available = set(available) if available is not None else set(_order)
    return [p for p in _order if p != primary and p in _available]


def select_next(
    current: str,
    chain: list[str],
) -> str | None:
    """Return the next provider in the fallback chain after ``current``.

    Parameters
    ----------
    current : str
        The provider that just failed.
    chain : list[str]
        Full ordered fallback chain (may include current).

    Returns
    -------
    str | None
        Next provider to try, or None if chain is exhausted.
    """
    try:
        idx = chain.index(current)
        if idx + 1 < len(chain):
            return chain[idx + 1]
    except ValueError:
        if chain:
            return chain[0]
    return None
