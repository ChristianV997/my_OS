import os

try:
    import requests as _requests
except ImportError:
    _requests = None

TTS_API_KEY = os.getenv("TTS_API_KEY")


def generate_voice(script: str) -> bytes:
    """Generate a TTS voiceover via ElevenLabs.

    Returns raw audio bytes, or an empty bytes object when offline / no key.
    """
    if not TTS_API_KEY or _requests is None:
        return b""

    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech"
        headers = {"xi-api-key": TTS_API_KEY}
        payload = {"text": script, "voice": "female_fast_tiktok"}
        res = _requests.post(url, json=payload, headers=headers, timeout=30)
        res.raise_for_status()
        return res.content
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return b""
