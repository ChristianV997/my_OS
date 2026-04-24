"""core.content.hook_scoring — score individual hooks from performance data."""
from __future__ import annotations

from typing import Any


def score(post: dict[str, Any]) -> float:
    """Compute a hook-level performance score.

    Formula: ``engagement * 0.7 + views * 1e-6``

    Parameters
    ----------
    post:
        Post feature dict with ``engagement`` and ``views`` keys.

    Returns
    -------
    float
    """
    engagement = float(post.get("engagement", 0.0))
    views = int(post.get("views", 0))
    return engagement * 0.7 + views * 1e-6
