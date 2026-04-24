"""Step 74 — Playbook Generator.

Generates an actionable content playbook from the winner patterns stored in
memory.  The initial heuristic is intentionally simple — take the first
winner's attributes and attach a fixed set of production rules.  This can be
expanded later with clustering or embedding-based approaches.
"""
from __future__ import annotations


def generate_playbook(memory: list[dict]) -> dict | None:
    """Return a playbook dict derived from winner entries in *memory*.

    Args:
        memory: list of pattern dicts (each with a ``result`` key).

    Returns:
        Playbook dict, or ``None`` if no winners exist in *memory*.
    """
    winners = [m for m in memory if m.get("result") == "WINNER"]

    if not winners:
        return None

    return {
        "hook": winners[0].get("hook"),
        "angle": winners[0].get("angle"),
        "format": winners[0].get("format"),
        "rules": [
            "fast cuts",
            "close visuals",
            "loop ending",
        ],
    }
