"""core.content.feedback — evaluate video performance and classify outcomes."""
from __future__ import annotations

from typing import Any

WINNER_MIN_VIEWS = 10_000
WINNER_MIN_ENGAGEMENT = 0.05
LOSER_MAX_VIEWS = 5_000


def evaluate(video: dict[str, Any]) -> str:
    """Classify a video as ``"WINNER"``, ``"LOSER"``, or ``"NEUTRAL"``.

    A video is a **WINNER** when it has at least :data:`WINNER_MIN_VIEWS` views
    and an engagement rate ≥ :data:`WINNER_MIN_ENGAGEMENT`.  A video is a
    **LOSER** when it has fewer than :data:`LOSER_MAX_VIEWS` views.  Otherwise
    it is **NEUTRAL**.

    Parameters
    ----------
    video:
        Dict with ``views``, ``likes``, and ``comments`` keys (all numeric).

    Returns
    -------
    str
        ``"WINNER"``, ``"LOSER"``, or ``"NEUTRAL"``.
    """
    views = int(video.get("views", 0))
    likes = int(video.get("likes", 0))
    comments = int(video.get("comments", 0))

    engagement = (likes + comments) / max(views, 1)

    if views >= WINNER_MIN_VIEWS and engagement >= WINNER_MIN_ENGAGEMENT:
        return "WINNER"
    if views < LOSER_MAX_VIEWS:
        return "LOSER"
    return "NEUTRAL"


def log_to_memory(
    video: dict[str, Any],
    hook: str,
    angle: str,
    fmt: str,
    result: str,
) -> None:
    """Append a feedback record to :data:`core.content.memory.CONTENT_MEMORY`.

    Parameters
    ----------
    video:
        Original video performance dict.
    hook:
        Hook text used in the video.
    angle:
        Content angle (e.g. ``"satisfaction"``).
    fmt:
        Video format label (e.g. ``"before/after"``).
    result:
        Classification from :func:`evaluate` (``"WINNER"`` / ``"LOSER"`` /
        ``"NEUTRAL"``).
    """
    from core.content.memory import store

    store(
        {
            "hook": hook,
            "angle": angle,
            "format": fmt,
            "result": result,
            "views": video.get("views", 0),
            "likes": video.get("likes", 0),
            "comments": video.get("comments", 0),
        }
    )
