"""Data Integrity Layer — schema validation, UTM validation, attribution reconciliation.

Validates campaign, product and creative dicts at ingestion time.
Invalid records are rejected with a ValidationError so callers can decide
whether to drop, quarantine or surface the issue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class ValidationError(ValueError):
    """Raised when a record fails schema validation."""

    def __init__(self, entity: str, field_name: str, reason: str):
        self.entity = entity
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"[{entity}] field '{field_name}': {reason}")


# ---------------------------------------------------------------------------
# UTM helpers
# ---------------------------------------------------------------------------

_UTM_REQUIRED = frozenset({"utm_campaign", "utm_source", "utm_medium"})
_UTM_OPTIONAL = frozenset({"utm_content", "utm_term"})


def validate_utm(data: dict[str, Any]) -> list[str]:
    """Return list of missing required UTM fields.  Empty = valid."""
    return [k for k in _UTM_REQUIRED if not data.get(k)]


def reconcile_attribution(data: dict[str, Any]) -> dict[str, Any]:
    """Fill missing utm_* fields with sensible defaults for downstream use.

    Does *not* mutate the original dict.
    """
    out = dict(data)
    out.setdefault("utm_campaign", "unknown_campaign")
    out.setdefault("utm_source", "unknown_source")
    out.setdefault("utm_medium", "unknown_medium")
    out.setdefault("utm_content", "")
    out.setdefault("utm_term", "")
    return out


# ---------------------------------------------------------------------------
# Campaign schema
# ---------------------------------------------------------------------------

_CAMPAIGN_REQUIRED: dict[str, type] = {
    "campaign_id": str,
    "spend": (int, float),
    "revenue": (int, float),
}

_CAMPAIGN_POSITIVE = frozenset({"spend", "revenue"})


def _type_name(t: type | tuple) -> str:
    """Return a human-readable type name for error messages."""
    if isinstance(t, tuple):
        return " or ".join(x.__name__ for x in t)
    return t.__name__


def validate_campaign(campaign: dict[str, Any]) -> None:
    """Raise ValidationError if *campaign* does not meet schema requirements."""
    for fname, ftype in _CAMPAIGN_REQUIRED.items():
        if fname not in campaign:
            raise ValidationError("campaign", fname, "missing required field")
        if not isinstance(campaign[fname], ftype):
            raise ValidationError(
                "campaign", fname,
                f"expected {_type_name(ftype)}, got {type(campaign[fname]).__name__}",
            )

    for fname in _CAMPAIGN_POSITIVE:
        if campaign.get(fname, 0) < 0:
            raise ValidationError("campaign", fname, "value must be non-negative")

    # UTM validation — warn via missing list; campaigns without UTM are rejected
    missing_utm = validate_utm(campaign)
    if missing_utm:
        raise ValidationError("campaign", "utm", f"missing required UTM fields: {missing_utm}")


# ---------------------------------------------------------------------------
# Product schema
# ---------------------------------------------------------------------------

_PRODUCT_REQUIRED: dict[str, type] = {
    "name": str,
    "score": (int, float),
}


def validate_product(product: dict[str, Any]) -> None:
    """Raise ValidationError if *product* does not meet schema requirements."""
    for fname, ftype in _PRODUCT_REQUIRED.items():
        if fname not in product:
            raise ValidationError("product", fname, "missing required field")
        if not isinstance(product[fname], ftype):
            raise ValidationError(
                "product", fname,
                f"expected {_type_name(ftype)}, got {type(product[fname]).__name__}",
            )

    if not product.get("name"):
        raise ValidationError("product", "name", "name must be a non-empty string")

    score = product.get("score", 0)
    if not (0.0 <= score <= 1.0):
        raise ValidationError("product", "score", f"score {score} not in [0, 1]")


# ---------------------------------------------------------------------------
# Creative schema
# ---------------------------------------------------------------------------

_CREATIVE_REQUIRED: dict[str, type] = {
    "creative_id": str,
    "headline": str,
    "format": str,
}

_CREATIVE_FORMATS = frozenset({"image", "video", "carousel", "text"})


def validate_creative(creative: dict[str, Any]) -> None:
    """Raise ValidationError if *creative* does not meet schema requirements."""
    for fname, ftype in _CREATIVE_REQUIRED.items():
        if fname not in creative:
            raise ValidationError("creative", fname, "missing required field")
        if not isinstance(creative[fname], ftype):
            raise ValidationError(
                "creative", fname,
                f"expected {_type_name(ftype)}, got {type(creative[fname]).__name__}",
            )

    fmt = creative.get("format", "")
    if fmt not in _CREATIVE_FORMATS:
        raise ValidationError("creative", "format", f"'{fmt}' not in allowed formats {_CREATIVE_FORMATS}")


# ---------------------------------------------------------------------------
# Generic ingestion gate
# ---------------------------------------------------------------------------

_VALIDATORS = {
    "campaign": validate_campaign,
    "product": validate_product,
    "creative": validate_creative,
}


def ingest(entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Validate *data* as *entity_type* and return it (possibly enriched).

    Raises ValidationError on failure so callers can choose to drop/quarantine.
    Campaigns have their UTM fields reconciled (defaults filled) before return.
    """
    validator = _VALIDATORS.get(entity_type)
    if validator is None:
        raise ValueError(f"Unknown entity type: {entity_type!r}")

    validator(data)

    if entity_type == "campaign":
        data = reconcile_attribution(data)

    return data
