BANNED_PATTERNS = [
    "guaranteed results",
    "make money fast",
    "lose weight instantly",
]


def validate_ad_copy(script: str) -> bool:
    """Return False if the script contains any banned claim patterns."""
    lower = script.lower()
    return not any(p in lower for p in BANNED_PATTERNS)
