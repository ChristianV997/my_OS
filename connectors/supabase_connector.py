"""Supabase connector — persistent storage for MarketOS state.

Writes cycle summaries and event rows to a Supabase (PostgreSQL) table via
the Supabase REST API. Falls back silently when credentials are absent so
that the system keeps running in offline/CI environments.

Environment variables:
  SUPABASE_URL          Project URL, e.g. https://<ref>.supabase.co
  SUPABASE_SERVICE_KEY  ``service_role`` key (not the anon key)
"""
import datetime
import os

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_CYCLES_TABLE = "cycle_summaries"
_EVENTS_TABLE = "events"


def _headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _post(table: str, payload: dict | list) -> bool:
    """Insert one or more rows into *table*.  Returns True on success."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY) or _requests is None:
        return False

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    try:
        resp = _requests.post(url, json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
        return True
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_cycle_summary(summary: dict) -> bool:
    """Persist a cycle summary dict to the ``cycle_summaries`` table.

    The dict should contain at minimum ``total_cycles``, ``capital``,
    ``detected_regime``, and ``avg_roas``.  A UTC timestamp is appended
    automatically.
    """
    row = {
        **summary,
        "recorded_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    return _post(_CYCLES_TABLE, row)


def save_events(events: list[dict]) -> bool:
    """Bulk-insert a list of event rows (from the event log) into Supabase."""
    if not events:
        return True
    enriched = [
        {**e, "recorded_at": datetime.datetime.now(datetime.UTC).isoformat()}
        for e in events
    ]
    return _post(_EVENTS_TABLE, enriched)


def is_configured() -> bool:
    """True when Supabase credentials are present in the environment."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
