def compose_video(
    template_script: str,
    voice_audio: bytes,
    avatar_video: dict | None = None,
) -> dict:
    """Compose the final video from script, voice, and optional avatar.

    Returns a dict with the output file path (placeholder until a real
    video pipeline is wired up).
    """
    return {"file_path": "/tmp/final_video.mp4", "status": "stub"}
