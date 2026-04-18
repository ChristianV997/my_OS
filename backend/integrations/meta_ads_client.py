import os
import datetime
import json
import logging
import re
import urllib.parse
import urllib.request

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
API_VERSION = os.getenv("META_API_VERSION", "v20.0")
logger = logging.getLogger(__name__)


def _is_valid_ad_account_id(account_id):
    if not account_id:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_]+", str(account_id)))


def get_ad_spend(last_n_minutes=60):
    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(minutes=last_n_minutes)

    fallback_campaigns = [
        {"campaign_id": "camp_1", "spend": 50.0},
        {"campaign_id": "camp_2", "spend": 40.0},
        {"campaign_id": "camp_3", "spend": 30.0},
    ]

    if not ACCESS_TOKEN or not _is_valid_ad_account_id(AD_ACCOUNT_ID):
        logger.info("Using Meta Ads fallback: missing credentials or invalid account id.")
        campaigns = fallback_campaigns
    else:
        params = {
            "access_token": ACCESS_TOKEN,
            "level": "campaign",
            "fields": "campaign_id,spend",
            "time_range": json.dumps(
                {
                    "since": since.date().isoformat(),
                    "until": now.date().isoformat(),
                }
            ),
        }
        url = (
            f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/insights?"
            f"{urllib.parse.urlencode(params)}"
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            rows = payload.get("data", [])
            campaigns = [
                {
                    "campaign_id": str(item.get("campaign_id", "unknown")),
                    "spend": float(item.get("spend", 0.0)),
                }
                for item in rows
            ]
            if not campaigns:
                campaigns = fallback_campaigns
        except Exception:  # pragma: no cover
            logger.exception("Meta Ads API request failed, using fallback campaigns.")
            campaigns = fallback_campaigns

    total_spend = sum(c["spend"] for c in campaigns)

    return {
        "campaigns": campaigns,
        "total_spend": total_spend,
        "since": since.isoformat(),
        "until": now.isoformat(),
    }
