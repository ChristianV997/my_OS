"""Campaign data validator.

Wraps core.data_integrity to provide a Pydantic-style validate_campaign()
that returns a dict-like object.  If Pydantic is available it is used; 
otherwise a lightweight dataclass is returned so the module works without
optional dependencies.
"""
from __future__ import annotations

from typing import Any

from core.data_integrity import validate_utm, reconcile_attribution


# ---------------------------------------------------------------------------
# Validated campaign result
# ---------------------------------------------------------------------------


class CampaignRecord:
    """Holds a validated, normalised campaign state dict."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # Allow dict-like access so callers can do record["roas"] etc.
    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __repr__(self) -> str:  # pragma: no cover
        return f"CampaignRecord({self._data!r})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_campaign(raw: dict[str, Any]) -> CampaignRecord:
    """Validate and normalise a raw campaign state dict.

    Fills missing UTM fields with safe defaults (via reconcile_attribution)
    and ensures numeric fields are present with sensible fallbacks.
    Raises ValueError if the dict is structurally invalid (e.g. not a dict).
    """
    if not isinstance(raw, dict):
        raise ValueError(f"validate_campaign expects a dict, got {type(raw)}")

    # Fill UTM defaults
    data = reconcile_attribution(raw)

    # Ensure numeric signal fields exist
    for field in ("roas", "ctr", "cvr", "spend", "revenue", "profit"):
        data.setdefault(field, 0.0)

    # Surface any UTM warnings (non-fatal)
    missing_utm = validate_utm(data)
    if missing_utm:
        import logging
        logging.getLogger(__name__).warning("Missing UTM fields: %s", missing_utm)

    return CampaignRecord(data)
