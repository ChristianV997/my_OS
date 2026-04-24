HOOKS = [
    "This changed everything…",
    "Nobody is talking about this…",
    "I wish I knew this sooner…",
    "This product is going viral for a reason…",
    "Stop wasting money on this…",
]


def inject_hooks(script: str) -> list[str]:
    """Prepend each hook in *HOOKS* to *script*, returning one variant per hook."""
    return [f"{hook}\n{script}" for hook in HOOKS]
