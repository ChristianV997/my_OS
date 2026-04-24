import os

try:
    import requests as _requests
except ImportError:
    _requests = None

from core.config_ads import TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID

BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

HEADERS = {"Access-Token": TIKTOK_ACCESS_TOKEN or ""}


def upload_creative(file_path: str) -> dict:
    """Upload a video creative to TikTok Ads.

    Falls back to a stub when credentials or requests are unavailable.
    """
    _FALLBACK = {"data": {"video_id": "tt_mock_video_1"}}

    if not (TIKTOK_ACCESS_TOKEN and TIKTOK_ADVERTISER_ID) or _requests is None:
        return _FALLBACK

    if not os.path.exists(file_path):
        return _FALLBACK

    try:
        url = f"{BASE_URL}/file/video/ad/upload/"
        with open(file_path, "rb") as fh:
            files = {"video_file": fh}
            data = {"advertiser_id": TIKTOK_ADVERTISER_ID}
            res = _requests.post(url, headers=HEADERS, files=files, data=data, timeout=60)
            res.raise_for_status()
            return res.json()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _FALLBACK
