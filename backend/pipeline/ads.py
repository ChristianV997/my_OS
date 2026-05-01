"""ads — format hooks into structured ad objects."""
from __future__ import annotations

_CTAS = {
    "finance":      "Start Saving Today",
    "productivity": "Try It Free",
    "ecommerce":    "Shop Now",
    "marketing":    "Grow Your Business",
    "review":       "See Reviews",
    "lifestyle":    "Discover More",
    "beauty":       "Shop the Look",
    "business":     "Scale Now",
}

_DEFAULT_CTA = "Learn More"


def format_ads(hooks: list[dict]) -> list[dict]:
    ads = []
    for h in hooks:
        category = h["category"]
        cta = _CTAS.get(category, _DEFAULT_CTA)
        headline = h["hook"][:80]
        raw_text = f"{h['hook']} | Engagement score: {h['engagement']:.2f}"
        primary_text = raw_text[:200]
        ads.append({
            "headline":     headline,
            "primary_text": primary_text,
            "call_to_action": cta,
            "category":     category,
            "source":       h["source"],
            "source_url":   h["url"],
            "external_id":  h["external_id"],
            "engagement":   h["engagement"],
        })
    return ads
