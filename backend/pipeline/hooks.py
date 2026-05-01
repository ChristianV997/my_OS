"""hooks — generate ad hook lines from filtered signals."""
from __future__ import annotations
from backend.signals.base import BaseSignal

_TEMPLATES = [
    "You won't believe this: {text}",
    "Stop what you're doing — {text}",
    "The secret nobody tells you: {text}",
    "Everyone is switching because: {text}",
    "Here's why this matters: {text}",
]


def generate_hooks(signals: list[BaseSignal]) -> list[dict]:
    hooks = []
    for i, sig in enumerate(signals):
        template = _TEMPLATES[i % len(_TEMPLATES)]
        hook_text = sig["raw_text"][:70]
        hooks.append({
            "hook": template.format(text=hook_text),
            "source": sig["source"],
            "category": sig["category"],
            "engagement": sig["engagement"],
            "external_id": sig["external_id"],
            "url": sig["url"],
        })
    return hooks
