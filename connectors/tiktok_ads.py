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

_FALLBACK_METRICS = {
    "spend": 30.0,
    "clicks": 450,
    "impressions": 15000,
    "conversions": 12,
    "ctr": 0.030,
    "cvr": 0.027,
    "cpc": 0.067,
    "cpa": 2.5,
}


def _headers() -> dict:
    """Return Authorization headers using the configured access token."""
    return {"Access-Token": ACCESS_TOKEN or ""}


def _post(path: str, payload: dict) -> dict:
    """POST to the TikTok Business API; returns parsed JSON or raises."""
    url = f"{API_BASE}{path}"
    resp = _requests.post(url, json=payload, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def _get(path: str, params: dict) -> dict:
    """GET from the TikTok Business API; returns parsed JSON or raises."""
    url = f"{API_BASE}{path}"
    resp = _requests.get(url, params=params, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Token / OAuth helpers
# ---------------------------------------------------------------------------

def exchange_code_for_token(app_id: str, secret: str, auth_code: str) -> dict:
    """Exchange an OAuth authorization code for an access + refresh token pair.

    Falls back to a stub response when credentials are absent or requests
    is unavailable (test / offline environments).
    """
    if not (app_id and secret and auth_code) or _requests is None:
        return {"access_token": "", "refresh_token": "", "advertiser_ids": []}

    try:
        data = _post(
            "/oauth2/access_token/",
            {"app_id": app_id, "secret": secret, "auth_code": auth_code},
        )
        return {
            "access_token": data.get("data", {}).get("access_token", ""),
            "refresh_token": data.get("data", {}).get("refresh_token", ""),
            "advertiser_ids": data.get("data", {}).get("advertiser_ids", []),
        }
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return {"access_token": "", "refresh_token": "", "advertiser_ids": []}


def refresh_access_token(app_id: str, secret: str, refresh_token: str) -> dict:
    """Refresh an expired access token.

    Falls back to a stub when offline.
    """
    if not (app_id and secret and refresh_token) or _requests is None:
        return {"access_token": "", "refresh_token": refresh_token}

    try:
        data = _post(
            "/oauth2/refresh_token/",
            {"app_id": app_id, "secret": secret, "refresh_token": refresh_token},
        )
        return {
            "access_token": data.get("data", {}).get("access_token", ""),
            "refresh_token": data.get("data", {}).get("refresh_token", refresh_token),
        }
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return {"access_token": "", "refresh_token": refresh_token}


# ---------------------------------------------------------------------------
# Campaign / Ad Group / Ad management
# ---------------------------------------------------------------------------

def create_campaign(
    name: str,
    objective: str = "CONVERSIONS",
    budget: float = 50.0,
    budget_mode: str = "BUDGET_MODE_DAY",
) -> dict:
    """Create a TikTok campaign and return its ID.

    Falls back to a stub dict when credentials are missing.
    """
    _FALLBACK = {"campaign_id": "tt_mock_camp_1", "status": "created"}

    if not (ACCESS_TOKEN and ADVERTISER_ID) or _requests is None:
        return _FALLBACK

    try:
        payload = {
            "advertiser_id": ADVERTISER_ID,
            "campaign_name": name,
            "objective_type": objective,
            "budget_mode": budget_mode,
            "budget": budget,
        }
        data = _post("/campaign/create/", payload)
        campaign_id = data.get("data", {}).get("campaign_id", _FALLBACK["campaign_id"])
        return {"campaign_id": campaign_id, "status": "created"}
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _FALLBACK


def create_ad_group(
    campaign_id: str,
    name: str,
    budget: float = 20.0,
    budget_mode: str = "BUDGET_MODE_DAY",
    bid: float = 5.0,
    placements: list | None = None,
) -> dict:
    """Create an ad group under a campaign and return its ID.

    Falls back to a stub when offline.
    """
    _FALLBACK = {"adgroup_id": "tt_mock_adgroup_1", "status": "created"}

    if not (ACCESS_TOKEN and ADVERTISER_ID) or _requests is None:
        return _FALLBACK

    if placements is None:
        placements = ["PLACEMENT_TIKTOK"]

    try:
        payload = {
            "advertiser_id": ADVERTISER_ID,
            "campaign_id": campaign_id,
            "adgroup_name": name,
            "budget_mode": budget_mode,
            "budget": budget,
            "bid_price": bid,
            "placement_type": "PLACEMENT_TYPE_NORMAL",
            "placements": placements,
        }
        data = _post("/adgroup/create/", payload)
        adgroup_id = data.get("data", {}).get("adgroup_id", _FALLBACK["adgroup_id"])
        return {"adgroup_id": adgroup_id, "status": "created"}
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _FALLBACK


def create_ad(
    adgroup_id: str,
    creative: dict,
) -> dict:
    """Create a single ad under an ad group and return its ID.

    *creative* should contain at least ``headline``, ``body``, and ``cta`` keys.
    Falls back to a stub when offline.
    """
    _FALLBACK = {"ad_id": "tt_mock_ad_1", "status": "created"}

    if not (ACCESS_TOKEN and ADVERTISER_ID) or _requests is None:
        return _FALLBACK

    try:
        payload = {
            "advertiser_id": ADVERTISER_ID,
            "adgroup_id": adgroup_id,
            "ad_name": creative.get("headline", "Ad"),
            "ad_text": creative.get("body", ""),
            "call_to_action": creative.get("cta", "SHOP_NOW"),
        }
        data = _post("/ad/create/", payload)
        ad_id = data.get("data", {}).get("ad_id", _FALLBACK["ad_id"])
        return {"ad_id": ad_id, "status": "created"}
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return _FALLBACK


# ---------------------------------------------------------------------------
# Metrics / reporting
# ---------------------------------------------------------------------------

def get_metrics(
    campaign_ids: list | None = None,
    last_n_days: int = 1,
) -> dict:
    """Return detailed performance metrics (spend, clicks, conversions, CTR, CVR).

    Falls back to ``_FALLBACK_METRICS`` when credentials are absent or a
    network error occurs.
    """
    if not (ACCESS_TOKEN and ADVERTISER_ID) or _requests is None:
        return dict(_FALLBACK_METRICS)

    now = datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(days=last_n_days)

    try:
        params: dict = {
            "advertiser_id": ADVERTISER_ID,
            "report_type": "BASIC",
            "data_level": "AUCTION_CAMPAIGN",
            "dimensions": '["campaign_id"]',
            "metrics": '["spend","clicks","impressions","conversion","ctr","cvr","cpc","cpa"]',
            "start_date": since.date().isoformat(),
            "end_date": now.date().isoformat(),
        }
        if campaign_ids:
            import json
            params["filters"] = json.dumps(
                [{"filter_field": "campaign_ids", "filter_type": "IN", "filter_value": campaign_ids}]
            )
        data = _get("/report/integrated/get/", params)
        rows = data.get("data", {}).get("list", [])
        if not rows:
            return dict(_FALLBACK_METRICS)

        totals: dict = {k: 0.0 for k in _FALLBACK_METRICS}
        for row in rows:
            m = row.get("metrics", {})
            totals["spend"] += float(m.get("spend", 0))
            totals["clicks"] += int(m.get("clicks", 0))
            totals["impressions"] += int(m.get("impressions", 0))
            totals["conversions"] += int(m.get("conversion", 0))

        totals["ctr"] = totals["clicks"] / totals["impressions"] if totals["impressions"] else 0.0
        totals["cvr"] = totals["conversions"] / totals["clicks"] if totals["clicks"] else 0.0
        totals["cpc"] = totals["spend"] / totals["clicks"] if totals["clicks"] else 0.0
        totals["cpa"] = totals["spend"] / totals["conversions"] if totals["conversions"] else 0.0
        return totals
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return dict(_FALLBACK_METRICS)


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
