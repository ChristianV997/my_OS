def build_timeline(hook: str, clips: list[str], script: str) -> dict:
    """Build a simple video timeline from hook text, UGC clips, and a script."""
    timeline_items = [
        {"type": "text_overlay", "text": hook, "duration": 2},
    ]

    if clips:
        timeline_items.append({"type": "clip", "source": clips[0]})

    timeline_items.append({"type": "text_overlay", "text": script[:80]})

    if len(clips) > 1:
        timeline_items.append({"type": "clip", "source": clips[1]})
    elif clips:
        timeline_items.append({"type": "clip", "source": clips[0]})

    timeline_items.append({"type": "cta", "text": "Shop now"})

    return {"timeline": timeline_items}
