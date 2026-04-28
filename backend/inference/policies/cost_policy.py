"""backend.inference.policies.cost_policy — provider cost estimation.

Used by the routing policy to prefer cheaper providers when all else is equal.
Cost estimates are in fractional USD per 1000 tokens (rough approximations;
update as pricing changes).
"""
from __future__ import annotations

# USD per 1,000 tokens (rough estimates for reference routing only)
_COST_PER_1K: dict[str, float] = {
    "openai":  0.002,    # gpt-4o-mini
    "litellm": 0.002,    # depends on backend
    "vllm":    0.0001,   # self-hosted — near-zero
    "ollama":  0.0,      # free (local)
    "airllm":  0.0,      # free (local)
    "mock":    0.0,      # free (test)
}

_DEFAULT_COST = 0.001  # fallback for unknown providers


class CostPolicy:
    """Provides cost estimates for providers and tokens."""

    def __init__(self, overrides: dict[str, float] | None = None) -> None:
        self._costs = dict(_COST_PER_1K)
        if overrides:
            self._costs.update(overrides)

    def estimate(self, provider: str, tokens: int = 1000) -> float:
        """Estimate cost in USD for generating `tokens` tokens with `provider`."""
        rate = self._costs.get(provider, _DEFAULT_COST)
        return rate * (tokens / 1000.0)

    def cheapest(self, providers: list[str]) -> str | None:
        """Return the cheapest provider from a list, or None if list is empty."""
        if not providers:
            return None
        return min(providers, key=lambda p: self._costs.get(p, _DEFAULT_COST))

    def rank(self, providers: list[str]) -> list[str]:
        """Return providers sorted ascending by cost (cheapest first)."""
        return sorted(providers, key=lambda p: self._costs.get(p, _DEFAULT_COST))
