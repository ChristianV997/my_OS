def generate_avatar_video(script: str, voice_audio: bytes) -> dict:
    """Generate a UGC-avatar video (HeyGen / D-ID placeholder).

    Returns a stub dict when no external service is configured.
    """
    return {"video_url": None, "status": "stub"}
