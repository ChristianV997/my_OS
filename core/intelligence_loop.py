"""core.intelligence_loop — signal enrichment via PatternStore and calibration.

Takes raw product keywords discovered by signal adapters and enriches them
with pattern intelligence before they feed into the simulation scoring layer.

Enrichment steps:
  1. Deduplicate and normalize keyword list
  2. Boost keywords that match proven top_hooks from PatternStore
  3. Annotate with hook affinity from HookPredictor
  4. Annotate with calibration readiness (are we ready to predict this?)
  5. Return ranked IdeaRecord list (product, priority, hook_affinity, calibrated)

Used by orchestrator._run_signal_ingestion() to guide the next
simulation scoring cycle with pattern-informed context.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def run_intelligence(keywords: list[str]) -> list[dict]:
    """Enrich raw keywords with pattern + calibration context.

    Returns a list of idea dicts sorted by priority (highest first):
      {
        "product":       str,
        "priority":      float,   # 0–1 composite score
        "hook_affinity": float,   # PatternStore hook boost
        "calibrated":    bool,    # CalibrationStore has enough data
        "top_hooks":     list,    # best hooks for this product
      }
    """
    seen: set[str] = set()
    candidates: list[str] = []
    for kw in (keywords or []):
        base = " ".join(str(kw).strip().split())
        if base and base not in seen:
            seen.add(base)
            candidates.append(base)

    if not candidates:
        return []

    # Pull pattern context (fails gracefully — returns empty dicts)
    top_hooks:   list[str]        = _get_top_hooks()
    hook_scores: dict[str, float] = _get_hook_scores()

    ideas: list[dict] = []
    for product in candidates:
        product_lower = product.lower()

        # Hook affinity: does any proven hook keyword overlap with this product?
        hook_affinity = 0.0
        for hook in top_hooks:
            if any(w in product_lower for w in hook.lower().split()):
                hook_affinity = max(hook_affinity, hook_scores.get(hook, 0.5))

        # Calibration: does CalibrationStore have data for this product?
        calibrated = _is_calibrated(product)

        # Playbook: does a playbook exist with high confidence?
        pb_boost, pb_hooks = _playbook_boost(product)

        # Priority composite:
        #   base=0.5 + hook_affinity bonus + calibration bonus + playbook bonus
        priority = min(1.0, 0.5 + 0.2 * hook_affinity + 0.15 * pb_boost
                       + (0.15 if calibrated else 0.0))

        ideas.append({
            "product":       product,
            "priority":      round(priority, 4),
            "hook_affinity": round(hook_affinity, 4),
            "calibrated":    calibrated,
            "top_hooks":     pb_hooks or top_hooks[:3],
        })

    ideas.sort(key=lambda x: x["priority"], reverse=True)
    _log.debug("intelligence_loop_enriched count=%d top=%s",
               len(ideas), ideas[0]["product"] if ideas else "none")
    return ideas


# ── helpers (all fail-safe) ───────────────────────────────────────────────────

def _get_top_hooks() -> list[str]:
    try:
        from core.content.patterns import pattern_store
        return pattern_store.get_top_hooks(n=5)
    except Exception:
        return []


def _get_hook_scores() -> dict[str, float]:
    try:
        from core.content.patterns import pattern_store
        return pattern_store.get_patterns().get("hook_scores", {})
    except Exception:
        return {}


def _is_calibrated(product: str) -> bool:
    try:
        from simulation.calibration import calibration_store
        # Consider calibrated if we have at least 5 paired records for this product
        summary = calibration_store.summary()
        by_product = summary.get("by_product", {})
        return by_product.get(product, {}).get("n", 0) >= 5
    except Exception:
        return False


def _playbook_boost(product: str) -> tuple[float, list[str]]:
    """Return (confidence_boost 0-1, top_hooks) from playbook memory."""
    try:
        from core.content.playbook import playbook_memory
        pb = playbook_memory.get(product)
        if pb is not None:
            return float(getattr(pb, "confidence", 0.0)), list(getattr(pb, "top_hooks", []))
    except Exception:
        pass
    return 0.0, []
