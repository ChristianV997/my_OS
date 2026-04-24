try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None


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
