"""Supabase persistent-state client (Priority 1).

Provides three operations against Supabase REST API:
  save_state(state_dict)   — upserts to ``system_state`` table
  load_state()             — returns last saved state dict (or None)
  append_events(rows)      — bulk inserts to ``events`` table

Falls back silently when credentials are absent so the system keeps running
in offline / CI environments.

Environment variables:
  SUPABASE_URL                Project URL, e.g. https://<ref>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service_role key (not the anon key)

Required Supabase tables (run once in dashboard):
  create table system_state (
      id text primary key,
      data jsonb,
      updated_at timestamptz default now()
  );
  create table events (
      id bigserial primary key,
      data jsonb,
      created_at timestamptz default now()
  );
"""
import datetime
import os

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_STATE_TABLE = "system_state"
_EVENTS_TABLE = "events"
_STATE_ID = "default"


def _is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and _requests is not None)


def _headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _rest_url(table: str) -> str:
    return f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"


def save_state(state_dict: dict) -> bool:
    """Upsert *state_dict* to the ``system_state`` table under a fixed ID.

    Returns True on success, False when credentials are absent or on error.
    """
    if not _is_configured():
        return False

    payload = {
        "id": _STATE_ID,
        "data": state_dict,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        resp = _requests.post(
            _rest_url(_STATE_TABLE),
            json=payload,
            headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return False


def load_state() -> dict | None:
    """Return the last saved state dict, or None when unavailable."""
    if not _is_configured():
        return None

    try:
        resp = _requests.get(
            _rest_url(_STATE_TABLE),
            params={"id": f"eq.{_STATE_ID}", "select": "data"},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if rows:
            return rows[0].get("data")
        return None
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return None


def append_events(rows: list[dict]) -> bool:
    """Bulk-insert *rows* into the ``events`` table.

    Returns True on success (including empty list), False on error.
    """
    if not rows:
        return True
    if not _is_configured():
        return False

    payload = [
        {"data": row, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        for row in rows
    ]
    try:
        resp = _requests.post(
            _rest_url(_EVENTS_TABLE),
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return False


def is_configured() -> bool:
    """True when Supabase credentials are present in the environment."""
    return _is_configured()
