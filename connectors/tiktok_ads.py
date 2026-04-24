import os
import datetime

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
ADVERTISER_ID = os.getenv("TIKTOK_ADVERTISER_ID")
API_BASE = "https://business-api.tiktok.com/open_api/v1.3"

_FALLBACK_CAMPAIGNS = [
    {"campaign_id": "tt_camp_1", "spend": 35.0},
    {"campaign_id": "tt_camp_2", "spend": 25.0},
]


def get_ad_spend(last_n_minutes: int = 60) -> dict:
    """Return campaign spend from TikTok Ads, falling back to mock data."""
    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(minutes=last_n_minutes)

    campaigns = _FALLBACK_CAMPAIGNS

    if ACCESS_TOKEN and ADVERTISER_ID and _requests is not None:
        try:
            url = f"{API_BASE}/report/integrated/get/"
            headers = {"Access-Token": ACCESS_TOKEN}
            params = {
                "advertiser_id": ADVERTISER_ID,
                "report_type": "BASIC",
                "data_level": "AUCTION_CAMPAIGN",
                "dimensions": '["campaign_id"]',
                "metrics": '["spend"]',
                "start_date": since.date().isoformat(),
                "end_date": now.date().isoformat(),
            }
            resp = _requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("data", {}).get("list", [])
            parsed = [
                {
                    "campaign_id": row["dimensions"]["campaign_id"],
                    "spend": float(row["metrics"].get("spend", 0)),
                }
                for row in rows
                if row.get("dimensions", {}).get("campaign_id")
            ]
            if parsed:
                campaigns = parsed
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            campaigns = _FALLBACK_CAMPAIGNS

    total_spend = sum(c["spend"] for c in campaigns)
    return {
        "campaigns": campaigns,
        "total_spend": total_spend,
        "since": since.isoformat(),
        "until": now.isoformat(),
    }
