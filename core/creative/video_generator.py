import os

try:
    import requests as _requests
except ImportError:
    _requests = None

RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")


def generate_video(prompt: str) -> dict:
    """Generate a short video from a text prompt via Runway ML.

    Falls back to a stub dict when the API key is absent or requests
    is unavailable (offline / test environments).
    """
    _FALLBACK = {"video_url": None, "status": "stub"}

    if not RUNWAY_API_KEY or _requests is None:
        return _FALLBACK

    try:
        url = "https://api.runwayml.com/v1/generate"
        headers = {
            "Authorization": f"Bearer {RUNWAY_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt, "duration": 8, "resolution": "720p"}
        res = _requests.post(url, json=payload, headers=headers, timeout=120)
        res.raise_for_status()
        return res.json()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _FALLBACK
