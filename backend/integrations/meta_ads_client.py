import os
import datetime

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")


def get_ad_spend(last_n_minutes=60):
    # Placeholder for real API integration
    # Replace with facebook_business SDK calls

    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(minutes=last_n_minutes)

    # Simulated structure for now (safe fallback)
    spend = 120.0

    return {
        "spend": spend,
        "since": since.isoformat(),
        "until": now.isoformat(),
        "campaign_id": "mock_campaign"
    }
