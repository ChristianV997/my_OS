"""Enhanced capital allocation engine for Phase 2.

Rules:
- ROAS > 2 → increase budget by 20–50 % (proportional to performance)
- ROAS < 1 → reduce budget or kill the pod
- Enforces a per-pod daily budget cap
- Tracks cumulative per-pod spend

This module complements the simpler ``core.capital`` module; the
``CapitalEngineV2`` is used by ``core.loop_v3``.
"""

from __future__ import annotations

# Default thresholds (can be overridden on construction)
SCALE_ROAS_THRESHOLD: float = 2.0   # ROAS must exceed this to scale
KILL_ROAS_THRESHOLD: float = 1.0    # ROAS below this triggers kill/reduce
MIN_SCALE_FACTOR: float = 0.20      # +20 % minimum budget increase
MAX_SCALE_FACTOR: float = 0.50      # +50 % maximum budget increase
REDUCE_FACTOR: float = 0.50         # halve budget before killing
DEFAULT_DAILY_CAP: float = 500.0    # per-pod daily budget ceiling
MAX_CONCURRENT_PODS: int = 10       # hard cap on simultaneous active pods


class CapitalEngineV2:
    """Controls dynamic budget scaling across pods.

    Parameters
    ----------
    scale_threshold:
        Minimum ROAS to qualify for budget increase.
    kill_threshold:
        ROAS below which a pod is reduced then killed.
    min_scale_factor:
        Minimum fractional budget increase when scaling (0.20 = +20 %).
    max_scale_factor:
        Maximum fractional budget increase when scaling (0.50 = +50 %).
    reduce_factor:
        Fraction by which a struggling pod's budget is cut before killing.
    daily_cap:
        Maximum daily budget allowed for any single pod.
    max_concurrent_pods:
        Maximum number of simultaneously active pods.
    """

    def __init__(
        self,
        scale_threshold: float = SCALE_ROAS_THRESHOLD,
        kill_threshold: float = KILL_ROAS_THRESHOLD,
        min_scale_factor: float = MIN_SCALE_FACTOR,
        max_scale_factor: float = MAX_SCALE_FACTOR,
        reduce_factor: float = REDUCE_FACTOR,
        daily_cap: float = DEFAULT_DAILY_CAP,
        max_concurrent_pods: int = MAX_CONCURRENT_PODS,
    ) -> None:
        self.scale_threshold = scale_threshold
        self.kill_threshold = kill_threshold
        self.min_scale_factor = min_scale_factor
        self.max_scale_factor = max_scale_factor
        self.reduce_factor = reduce_factor
        self.daily_cap = daily_cap
        self.max_concurrent_pods = max_concurrent_pods
        # Cumulative per-pod spend tracking: {pod_id: total_spend}
        self._spend_ledger: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Spend tracking
    # ------------------------------------------------------------------

    def record_spend(self, pod_id: str, amount: float) -> float:
        """Accumulate *amount* against *pod_id*; return new cumulative total."""
        self._spend_ledger[pod_id] = self._spend_ledger.get(pod_id, 0.0) + amount
        return self._spend_ledger[pod_id]

    def pod_spend(self, pod_id: str) -> float:
        """Return total tracked spend for *pod_id*."""
        return self._spend_ledger.get(pod_id, 0.0)

    def reset_spend(self, pod_id: str) -> None:
        """Reset the daily spend counter for *pod_id* (call at day rollover)."""
        self._spend_ledger.pop(pod_id, None)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _scale_factor_for_roas(self, roas: float) -> float:
        """Return a scale factor between min and max, proportional to ROAS.

        Linear interpolation between ``scale_threshold`` (→ min_factor) and
        ``scale_threshold * 2`` (→ max_factor).
        """
        upper = self.scale_threshold * 2.0
        t = min(max((roas - self.scale_threshold) / (upper - self.scale_threshold), 0.0), 1.0)
        return self.min_scale_factor + t * (self.max_scale_factor - self.min_scale_factor)

    def evaluate(self, pod) -> str:
        """Return ``'scale'``, ``'reduce'``, ``'kill'``, or ``'hold'``."""
        roas = pod.metrics.get("roas", 0.0)
        if roas > self.scale_threshold:
            return "scale"
        if roas < self.kill_threshold:
            # If budget is already very small, kill outright
            if pod.budget <= 5.0:
                return "kill"
            return "reduce"
        return "hold"

    def apply(self, pod) -> str:
        """Apply the capital decision to *pod* (mutates it in place).

        Returns the decision string: ``'scale'``, ``'reduce'``, ``'kill'``,
        or ``'hold'``.
        """
        decision = self.evaluate(pod)
        roas = pod.metrics.get("roas", 0.0)

        if decision == "scale":
            factor = self._scale_factor_for_roas(roas)
            new_budget = pod.budget * (1.0 + factor)
            pod.budget = min(new_budget, self.daily_cap)
            pod.status = "scaling"

        elif decision == "reduce":
            pod.budget = max(pod.budget * self.reduce_factor, 0.0)
            # If budget has effectively hit zero, kill
            if pod.budget < 1.0:
                pod.budget = 0.0
                pod.status = "killed"

        elif decision == "kill":
            pod.budget = 0.0
            pod.status = "killed"

        # Record incremental spend from current metrics cycle
        self.record_spend(pod.id, pod.metrics.get("spend", 0.0))

        return decision

    # ------------------------------------------------------------------
    # Budget allocation
    # ------------------------------------------------------------------

    def allocate_budget(self, pods: list, total_budget: float) -> dict[str, float]:
        """Distribute *total_budget* across active pods, capped at ``daily_cap``.

        Active pods are sorted by ROAS (descending) so top performers receive
        funds first when total_budget would be exceeded by even distribution.
        """
        active = [p for p in pods if p.status != "killed"]
        if not active:
            return {}

        # Sort by ROAS descending so winners get priority
        active.sort(key=lambda p: p.metrics.get("roas", 0.0), reverse=True)

        # Respect max_concurrent_pods
        active = active[: self.max_concurrent_pods]

        per_pod = total_budget / len(active)
        allocation: dict[str, float] = {}
        remaining = total_budget

        for pod in active:
            alloc = min(per_pod, self.daily_cap, remaining)
            allocation[pod.id] = round(alloc, 4)
            remaining -= alloc

        return allocation

    def enforce_daily_cap(self, pod) -> bool:
        """Return ``True`` and kill the pod if it has exceeded its daily cap."""
        if self.pod_spend(pod.id) >= self.daily_cap:
            pod.status = "killed"
            return True
        return False


capital_engine_v2 = CapitalEngineV2()
