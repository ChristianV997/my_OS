"""simulation.predictors.hooks — hook-level engagement predictor.

Scores a hook string using the live PatternStore scores (EMA-weighted
hook performance from historical classified events).

Falls back to a keyword heuristic when no pattern data is available
so it works immediately at cold start.
"""
from __future__ import annotations

import re
import threading
from typing import Any

# Keyword heuristics used when PatternStore has no data yet.
# Weights are based on commonly observed engagement patterns in e-commerce.
_URGENCY_KW  = re.compile(r"\b(urgent|now|today|limited|last|hurry|deal)\b", re.I)
_SOCIAL_KW   = re.compile(r"\b(people|everyone|trending|viral|popular|sold)\b", re.I)
_PROOF_KW    = re.compile(r"\b(proven|verified|tested|results|works|guarantee)\b", re.I)
_CURIOSITY_KW= re.compile(r"\b(secret|surprising|hidden|weird|unusual|never)\b", re.I)


def _keyword_score(hook: str) -> float:
    """Return a 0–1 heuristic score from hook keyword patterns."""
    score = 0.0
    if _URGENCY_KW.search(hook):   score += 0.4
    if _SOCIAL_KW.search(hook):    score += 0.3
    if _PROOF_KW.search(hook):     score += 0.2
    if _CURIOSITY_KW.search(hook): score += 0.2
    return min(score, 1.0)


class HookPredictor:
    """Predict engagement score for a hook string.

    Priority order:
      1. PatternStore.hook_scores (live EMA-weighted history)
      2. CalibrationStore top-hook statistics
      3. Keyword heuristic fallback
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: dict[str, float] = {}
        self._cache_ts: float = 0.0
        self._CACHE_TTL = 30.0  # refresh pattern scores at most every 30s

    def score(self, hook: str) -> float:
        """Return a 0–1 engagement score for a hook string."""
        if not hook:
            return 0.0

        self._refresh_cache()
        with self._lock:
            if hook in self._cache:
                return self._cache[hook]

        # fallback: keyword heuristic
        return _keyword_score(hook)

    def score_batch(self, hooks: list[str]) -> list[float]:
        return [self.score(h) for h in hooks]

    def _refresh_cache(self) -> None:
        import time
        now = time.time()
        with self._lock:
            if now - self._cache_ts < self._CACHE_TTL:
                return

        try:
            from core.content.patterns import pattern_store
            scores = pattern_store.get_patterns().get("hook_scores", {})
            if scores:
                # normalise to 0–1 range
                max_v = max(scores.values()) or 1.0
                with self._lock:
                    self._cache = {h: v / max_v for h, v in scores.items()}
                    self._cache_ts = now
        except Exception:
            pass

    def top_hooks(self, n: int = 5) -> list[str]:
        """Return the top-n hooks by predicted engagement score."""
        self._refresh_cache()
        with self._lock:
            cache = dict(self._cache)
        if cache:
            return sorted(cache, key=cache.get, reverse=True)[:n]  # type: ignore[arg-type]
        # cold start — return empty list
        return []


# module-level singleton
hook_predictor = HookPredictor()
