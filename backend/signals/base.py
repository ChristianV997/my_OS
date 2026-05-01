"""base — BaseSignal TypedDict shared across all scrapers."""
from typing import TypedDict


class BaseSignal(TypedDict):
    source: str
    raw_text: str
    engagement: float       # [0.0, 1.0]
    category: str
    timestamp: str          # ISO 8601
    url: str
    external_id: str
