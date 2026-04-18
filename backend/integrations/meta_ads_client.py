import os
import datetime

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")


def get_ad_spend(last_n_minutes=60):
    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(minutes=last_n_minutes)

    # MOCK multi-campaign breakdown (replace with real API later)
    campaigns = [
        {"campaign_id": "camp_1", "spend": 50.0},
        {"campaign_id": "camp_2", "spend": 40.0},
        {"campaign_id": "camp_3", "spend": 30.0},
    ]

    total_spend = sum(c["spend"] for c in campaigns)

    return {
        "campaigns": campaigns,
        "total_spend": total_spend,
        "since": since.isoformat(),
        "until": now.isoformat(),
    }
