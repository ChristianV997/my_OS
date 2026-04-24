def script_to_prompt(script: str) -> str:
    """Convert an ad script into a video generation prompt."""
    return (
        "Create a short vertical TikTok-style video.\n\n"
        f"{script}\n\n"
        "Style:\n"
        "- fast cuts\n"
        "- engaging hook in first 2 seconds\n"
        "- product-focused\n"
        "- high energy\n"
    )
