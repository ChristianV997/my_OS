import random


def select_clips(clips: list[str], k: int = 2) -> list[str]:
    """Randomly select up to *k* clips from *clips*."""
    return random.sample(clips, min(k, len(clips)))
