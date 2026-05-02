"""google_trends — mock Google Trends signal scraper."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from .base import BaseSignal, validate_signal

_TEXTS = [
    "best AI productivity tools to scale your business 2025",
    "how to make money with automation and ChatGPT",
    "passive income growth strategies that actually earn",
    "best budgeting tool to save money for millennials",
    "how to scale a dropshipping business in 2025",
    "side hustle growth hacks for extra income",
    "best credit card tool for rewards — worth the price",
    "how to earn from real estate with no money hack",
    "print on demand — worth it to scale your income",
    "best productivity system and automation tools for entrepreneurs",
    "how to get free stuff and save money on Amazon",
    "viral marketing growth strategies that earn results",
    "best online courses worth buying to make money",
    "how to scale a business on social media with automation",
    "best affiliate programs worth the price — high ticket earn",
    "how to automate your business and scale growth in 2025",
    "remote work productivity tools everyone needs to buy",
    "best way to save money and growth-hack subscriptions",
    "how to sell on Amazon FBA profitably — earn at scale",
    "trending products worth selling online for growth 2025",
]

_CATEGORIES = [
    "productivity", "finance", "finance", "finance", "ecommerce",
    "finance", "finance", "finance", "ecommerce", "productivity",
    "ecommerce", "marketing", "finance", "marketing", "marketing",
    "productivity", "productivity", "finance", "ecommerce", "ecommerce",
]


def _det_hash(query: str, i: int) -> int:
    return int(hashlib.md5(f"{query}:{i}".encode()).hexdigest(), 16)


def ingest_google_trends(query: str = "google trends rising") -> list[BaseSignal]:
    signals: list[BaseSignal] = []
    base_ts = datetime(2025, 5, 1, 7, 0, 0, tzinfo=timezone.utc)
    for i, text in enumerate(_TEXTS):
        h = _det_hash(query, i)
        search_volume = (h % 90) + 10
        rising_pct    = ((_det_hash(query, i + 100)) % 500) + 50
        norm_volume   = search_volume / 100.0
        norm_rising   = min(1.0, rising_pct / 500.0)
        raw_eng       = norm_volume * 0.6 + norm_rising * 0.4
        noise_factor  = 0.50 + (_det_hash(query, i + 500) % 51) / 100.0
        engagement    = min(1.0, round(raw_eng * noise_factor, 4))
        sig = BaseSignal(
            source="google_trends",
            raw_text=text,
            engagement=engagement,
            category=_CATEGORIES[i],
            timestamp=base_ts.isoformat(),
            url=f"https://trends.google.com/trends/explore?q={text.replace(' ', '%20')}",
            external_id=f"gt_{h % 10**12:012d}",
        )
        if not validate_signal(sig):
            continue
        signals.append(sig)
    return signals
