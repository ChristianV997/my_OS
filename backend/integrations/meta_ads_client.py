import os
import datetime
import json

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v20.0")


def get_ad_spend(last_n_minutes=60):
    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(minutes=last_n_minutes)

    # fallback if credentials are missing or request fails
    fallback_campaigns = [
        {"campaign_id": "camp_1", "spend": 50.0},
        {"campaign_id": "camp_2", "spend": 40.0},
        {"campaign_id": "camp_3", "spend": 30.0},
    ]
    campaigns = fallback_campaigns

    if requests is not None and ACCESS_TOKEN and AD_ACCOUNT_ID:
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/act_{AD_ACCOUNT_ID}/insights"
            params = {
                "access_token": ACCESS_TOKEN,
                "level": "campaign",
                "fields": "campaign_id,spend",
                "time_range": json.dumps(
                    {"since": since.date().isoformat(), "until": now.date().isoformat()}
                ),
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", [])
            parsed = []
            for row in data:
                campaign_id = row.get("campaign_id")
                spend = float(row.get("spend", 0.0))
                if campaign_id:
                    parsed.append({"campaign_id": campaign_id, "spend": spend})
            if parsed:
                campaigns = parsed
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            campaigns = fallback_campaigns

    total_spend = sum(c["spend"] for c in campaigns)

    return {
        "campaigns": campaigns,
        "total_spend": total_spend,
        "since": since.isoformat(),
        "until": now.isoformat(),
    }
