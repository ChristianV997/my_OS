"""simulation.features — feature extraction for simulation scoring.

Builds a fixed-length numeric feature vector from signals, outcomes, patterns,
and playbooks so that the scoring model operates on a consistent schema.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

# Canonical feature names — do not reorder; model weights depend on position.
FEATURE_NAMES = [
    # signal features
    "signal_score",
    "signal_velocity",
    # pattern features
    "hook_score",
    "angle_score",
    "regime_score",
    # playbook features
    "playbook_estimated_roas",
    "playbook_confidence",
    "playbook_evidence_count_log",
    # historical outcome features
    "hist_avg_roas",
    "hist_avg_ctr",
    "hist_avg_cvr",
    "hist_win_rate",
    "hist_sample_count_log",
    # engagement features
    "engagement_rate",
    # bias / intercept
    "bias",
]

_N = len(FEATURE_NAMES)


def _safe(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def extract(
    signal: dict,
    patterns: dict | None = None,
    playbook: Any | None = None,
    history: list[dict] | None = None,
) -> list[float]:
    """Return a fixed-length feature vector for one signal candidate.

    Parameters
    ----------
    signal:
        Dict with at least ``score`` (0–1 float) and optional ``velocity``.
    patterns:
        Output of ``core.content.patterns.extract_patterns()`` — has
        ``hook_scores``, ``angle_scores``, ``regime_scores``.
    playbook:
        A ``Playbook`` dataclass instance or dict; optional.
    history:
        List of past event dicts (roas, ctr, cvr, label) for this signal/product.
    """
    p = patterns or {}
    hook_scores: dict = p.get("hook_scores", {})
    angle_scores: dict = p.get("angle_scores", {})
    regime_scores: dict = p.get("regime_scores", {})

    product = signal.get("product", "")
    hook = signal.get("hook", "")
    angle = signal.get("angle", "")
    regime = signal.get("regime", signal.get("env_regime", ""))

    # best matching scores
    hook_score = hook_scores.get(hook, 0.0) if hook else (
        max(hook_scores.values()) if hook_scores else 0.0
    )
    angle_score = angle_scores.get(angle, 0.0) if angle else (
        max(angle_scores.values()) if angle_scores else 0.0
    )
    regime_score = regime_scores.get(regime, 0.0) if regime else (
        max(regime_scores.values()) if regime_scores else 0.0
    )

    # playbook features
    pb_roas = pb_conf = pb_ev = 0.0
    if playbook is not None:
        if hasattr(playbook, "estimated_roas"):
            pb_roas = _safe(playbook.estimated_roas)
            pb_conf = _safe(playbook.confidence)
            pb_ev = math.log1p(_safe(playbook.evidence_count))
        elif isinstance(playbook, dict):
            pb_roas = _safe(playbook.get("estimated_roas", 0))
            pb_conf = _safe(playbook.get("confidence", 0))
            pb_ev = math.log1p(_safe(playbook.get("evidence_count", 0)))

    # historical outcome features
    hist_roas = hist_ctr = hist_cvr = hist_wr = hist_n = 0.0
    if history:
        n = len(history)
        hist_roas = sum(_safe(r.get("roas", 0)) for r in history) / n
        hist_ctr = sum(_safe(r.get("ctr", 0)) for r in history) / n
        hist_cvr = sum(_safe(r.get("cvr", 0)) for r in history) / n
        hist_wr = sum(1 for r in history if r.get("label") == "WINNER") / n
        hist_n = math.log1p(n)

    eng = _safe(signal.get("engagement_rate", 0))

    return [
        _safe(signal.get("score", 0)),
        _safe(signal.get("velocity", 0)),
        _safe(hook_score),
        _safe(angle_score),
        _safe(regime_score),
        pb_roas,
        pb_conf,
        pb_ev,
        hist_roas,
        hist_ctr,
        hist_cvr,
        hist_wr,
        hist_n,
        eng,
        1.0,  # bias
    ]


def batch_extract(
    signals: list[dict],
    patterns: dict | None = None,
    playbooks: dict | None = None,
    history_map: dict[str, list[dict]] | None = None,
) -> list[list[float]]:
    """Extract features for a list of signals.

    Parameters
    ----------
    playbooks:
        Mapping of product name → Playbook (or dict).
    history_map:
        Mapping of product name → list of past events.
    """
    result = []
    for sig in signals:
        product = sig.get("product", "")
        pb = (playbooks or {}).get(product)
        hist = (history_map or {}).get(product)
        result.append(extract(sig, patterns=patterns, playbook=pb, history=hist))
    return result
