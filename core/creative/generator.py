"""core.creative.generator — ad creative generation utilities.

Provides two complementary generation strategies:

* :func:`generate_creative` — AI-powered single script via Anthropic Claude API.
* :func:`generate_creatives` — hook-template-based batch generator (Step 65).
"""
from __future__ import annotations

from typing import Any

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None

# ---------------------------------------------------------------------------
# Step 65 — hook-template generator
# ---------------------------------------------------------------------------

_HOOKS: dict[str, list[str]] = {
    "satisfaction": [
        "watch this",
        "this is so satisfying",
    ],
    "problem": [
        "this fixes...",
        "stop doing this wrong",
    ],
    "convenience": [
        "this saves so much time",
        "the easiest way to do this",
    ],
    "transformation": [
        "before vs after",
        "this changed everything",
    ],
}


def generate_creatives(product: str, angle: str) -> list[dict[str, Any]]:
    """Return hook-based creative variants for *product* and *angle*.

    Parameters
    ----------
    product:
        Product name to feature in each creative.
    angle:
        Content angle key (e.g. ``"satisfaction"``, ``"problem"``).

    Returns
    -------
    list[dict]
        Each dict contains ``hook``, ``body``, and ``cta`` keys.
    """
    hooks = _HOOKS.get(angle, [f"{angle} hook"])
    return [
        {
            "hook": h,
            "body": f"show {product} solving problem",
            "cta": "get it now",
        }
        for h in hooks
    ]


# ---------------------------------------------------------------------------
# AI-powered single-script generator
# ---------------------------------------------------------------------------


def generate_creative(product: str, angle: str) -> str:
    """Generate an ad script for *product* using the given *angle*.

    Uses the Anthropic Claude API when available; otherwise returns a
    deterministic placeholder so the system works offline / in tests.
    """
    if _anthropic is None or not hasattr(_anthropic, "Anthropic"):
        return (
            f"[Script] Product: {product} | Angle: {angle} | "
            "Hook: Discover the difference. | CTA: Shop now."
        )

    try:
        client = _anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a short TikTok ad script for '{product}'. "
                        f"Angle: {angle}. "
                        "Include a hook, problem, solution, and CTA. "
                        "Keep it under 60 words."
                    ),
                }
            ],
        )
        return msg.content[0].text.strip()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return (
            f"[Script] Product: {product} | Angle: {angle} | "
            "Hook: Discover the difference. | CTA: Shop now."
        )
