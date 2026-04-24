"""core.content.scoring — score organic posts for promotion eligibility."""
from __future__ import annotations

from typing import Any


def score(post: dict[str, Any]) -> float:
    """Compute a composite score for an organic post.

    Formula: ``engagement * 0.7 + views * 1e-6``

    Parameters
    ----------
    post:
        Post dict with ``engagement`` and ``views`` keys.

    Returns
    -------
    float
        Composite score (higher → better promotion candidate).
    """
    engagement = float(post.get("engagement", 0.0))
    views = int(post.get("views", 0))
    return engagement * 0.7 + views * 1e-6
