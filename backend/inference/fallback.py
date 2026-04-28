"""FallbackChain — thin public wrapper used by the router and callers.

Centralises fallback chain construction so callers don't import policy
classes directly.
"""
from __future__ import annotations

import os

from .policies.fallback_policy import FallbackPolicy

# Default exported chain instance — reflects INFERENCE_PROVIDERS env var.
default_chain: FallbackPolicy = FallbackPolicy()


def get_chain() -> list[str]:
    """Return the current ordered fallback chain (with mock guaranteed)."""
    return default_chain.with_guaranteed_mock()


def reload_chain() -> FallbackPolicy:
    """Re-read INFERENCE_PROVIDERS from the environment and return a fresh policy."""
    global default_chain
    default_chain = FallbackPolicy()
    return default_chain
