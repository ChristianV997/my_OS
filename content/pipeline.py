"""Step 74 — Content Feedback Pipeline.

Wires together the full content → data → patterns → playbook flow:

    post content
     → collect metrics
     → classify (WINNER / LOSER / NEUTRAL)
     → extract pattern
     → store in memory
     → generate playbook
     → feed into creative generator
"""
from __future__ import annotations

from content.feedback import evaluate
from content.pattern_extractor import extract_pattern
from content import memory as _mem
from content.playbook import generate_playbook


def run(video: dict) -> dict:
    """Process a single *video* through the full feedback pipeline.

    Args:
        video: raw video metadata dict.  Expected keys: ``views``, ``likes``,
               ``comments``, and optional creative-signal keys (``hook``,
               ``angle``, ``format``, ``pacing``, ``visual``).

    Returns:
        Result dict with keys:
        - ``result``   — classification ('WINNER' / 'LOSER' / 'NEUTRAL')
        - ``pattern``  — extracted creative pattern dict
        - ``playbook`` — current playbook (may be ``None``)
    """
    result = evaluate(video)
    pattern = extract_pattern(video)
    _mem.store(pattern, result)
    playbook = generate_playbook(_mem.get_all())

    return {
        "result": result,
        "pattern": pattern,
        "playbook": playbook,
    }


def run_batch(videos: list[dict]) -> list[dict]:
    """Run :func:`run` for every video in *videos* and return all results."""
    return [run(v) for v in videos]
