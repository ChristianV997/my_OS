import os

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")

_FALLBACK_CAMPAIGN = {"campaign_id": "meta_mock_camp_1", "status": "created"}


def create_campaign(name, objective="CONVERSIONS", status="PAUSED"):
    if not (ACCESS_TOKEN and AD_ACCOUNT_ID) or _requests is None:
        return dict(_FALLBACK_CAMPAIGN)

    base_url = f"https://graph.facebook.com/v19.0/{AD_ACCOUNT_ID}"
    url = f"{base_url}/campaigns"

    payload = {
        "name": name,
        "objective": objective,
        "status": status,
        "access_token": ACCESS_TOKEN,
    }

    try:
        response = _requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return dict(_FALLBACK_CAMPAIGN)


def get_campaign_insights(campaign_id, fields="spend,clicks,impressions"):
    if not ACCESS_TOKEN or _requests is None:
        return {"spend": 0, "clicks": 0, "impressions": 0}

    url = f"https://graph.facebook.com/v19.0/{campaign_id}/insights"
    params = {
        "fields": fields,
        "access_token": ACCESS_TOKEN,
    }

    try:
        response = _requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        rows = data.get("data", [])
        return rows[0] if rows else {}
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return {"spend": 0, "clicks": 0, "impressions": 0}
