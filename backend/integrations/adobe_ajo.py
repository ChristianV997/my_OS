"""Adobe Journey Optimizer (AJO) connector — backend integration (Priority 3).

Wraps the AJO REST API to pause underperforming campaigns and scale budgets
for high-ROAS winners in real time.

Falls back to stub responses when credentials are absent so the execution
loop continues uninterrupted in offline / CI environments.

Environment variables:
  ADOBE_AJO_TOKEN   Bearer token for AJO REST API
  ADOBE_IMS_ORG     IMS Organisation ID (x-gw-ims-org-id header)
"""
import os

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

_AJO_TOKEN = os.getenv("ADOBE_AJO_TOKEN", "")
_IMS_ORG = os.getenv("ADOBE_IMS_ORG", "")
_AJO_BASE = "https://journey-optimizer.adobe.io/restapi/v1"


def _is_configured() -> bool:
    return bool(_AJO_TOKEN and _requests is not None)


def _headers() -> dict:
    h = {
        "Authorization": f"Bearer {_AJO_TOKEN}",
        "Content-Type": "application/json",
    }
    if _IMS_ORG:
        h["x-gw-ims-org-id"] = _IMS_ORG
    return h


def _patch(campaign_id: str, payload: dict) -> dict:
    """PATCH a campaign object in AJO.  Returns result dict."""
    url = f"{_AJO_BASE}/campaigns/{campaign_id}"
    try:
        resp = _requests.patch(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.content else {"status": "ok", "campaign_id": campaign_id}
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        return {"error": str(exc), "campaign_id": campaign_id}


def pause_campaign(campaign_id: str) -> dict:
    """Pause an AJO campaign by ID.

    Returns a result dict with ``status`` and ``campaign_id`` keys.
    Falls back to ``{"status": "paused_mock", ...}`` when credentials absent.
    """
    if not _is_configured():
        return {"status": "paused_mock", "campaign_id": campaign_id}

    result = _patch(campaign_id, {"status": "stopped"})
    result.setdefault("status", "paused")
    return result


def scale_campaign(campaign_id: str, budget_multiplier: float = 1.5) -> dict:
    """Scale up an AJO campaign's daily budget by *budget_multiplier*.

    Returns a result dict with ``status``, ``campaign_id``, and
    ``budget_multiplier`` keys.  Falls back to stub when credentials absent.
    """
    if not _is_configured():
        return {
            "status": "scaled_mock",
            "campaign_id": campaign_id,
            "budget_multiplier": budget_multiplier,
        }

    result = _patch(
        campaign_id, {"budgetMultiplier": round(float(budget_multiplier), 4)}
    )
    result.setdefault("status", "scaled")
    result["budget_multiplier"] = budget_multiplier
    return result


def is_configured() -> bool:
    """True when AJO credentials are present in the environment."""
    return _is_configured()
