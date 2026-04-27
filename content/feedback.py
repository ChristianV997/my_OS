"""Step 74 — Content Feedback Engine.

Classifies a video as WINNER, LOSER, or NEUTRAL based on views and
engagement rate.
"""
from __future__ import annotations


def evaluate(video: dict) -> str:
    """Return 'WINNER', 'LOSER', or 'NEUTRAL' for *video*.

    Args:
        video: dict with at minimum the keys ``views``, ``likes``, and
               ``comments``.

    Returns:
        Classification string.
    """
    views = video["views"]
    engagement = (video["likes"] + video["comments"]) / max(views, 1)

    if views > 10000 and engagement > 0.05:
        return "WINNER"

    if views < 5000:
        return "LOSER"

    return "NEUTRAL"
