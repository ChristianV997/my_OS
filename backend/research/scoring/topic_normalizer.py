from __future__ import annotations

import re
import unicodedata

_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "how",
    "in",
    "of",
    "on",
    "the",
    "to",
    "vs",
    "with",
}


def normalize_topic(topic: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(topic or "")).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    tokens = [token for token in normalized.split() if token and token not in _STOPWORDS]
    return " ".join(tokens)


def topic_signature(topic: str) -> tuple[str, ...]:
    normalized = normalize_topic(topic)
    return tuple(sorted(set(normalized.split())))
