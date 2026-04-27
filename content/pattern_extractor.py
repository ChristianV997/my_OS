"""Step 74 — Pattern Extractor.

Extracts creative signal attributes from a video record.
"""
from __future__ import annotations


def extract_pattern(video: dict) -> dict:
    """Return a dict of content pattern attributes from *video*.

    Args:
        video: raw video metadata dict.

    Returns:
        Pattern dict with keys: hook, angle, format, pacing, visual.
    """
    return {
        "hook": video.get("hook"),
        "angle": video.get("angle"),
        "format": video.get("format"),
        "pacing": video.get("pacing"),
        "visual": video.get("visual"),
    }
