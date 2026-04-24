"""Step 74 — Content Pattern Memory.

Stores classified content patterns in an in-process list so that
downstream components (playbook generator, creative optimizer) can
query past winners and losers.
"""
from __future__ import annotations

MEMORY: list[dict] = []


def store(pattern: dict, result: str) -> None:
    """Append *pattern* together with its *result* classification to MEMORY.

    Args:
        pattern: dict returned by :func:`content.pattern_extractor.extract_pattern`.
        result:  classification string — 'WINNER', 'LOSER', or 'NEUTRAL'.
    """
    MEMORY.append({**pattern, "result": result})


def clear() -> None:
    """Clear all stored patterns (useful for tests)."""
    MEMORY.clear()


def get_all() -> list[dict]:
    """Return a copy of the full memory list."""
    return list(MEMORY)
