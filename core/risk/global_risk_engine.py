"""Global Risk Engine — hard caps, central kill-switch, and risk-agent override.

All budget actions produced by agents are filtered through this engine before
being applied.  The engine maintains:

* max_daily_spend — absolute spend ceiling for a rolling 24-hour window
* max_drawdown    — maximum peak-to-trough capital loss allowed
* kill_switch     — boolean flag that vetoes all non-zero budget actions

Usage::

    engine = GlobalRiskEngine()

    # gate a proposed budget change
    safe_budget = engine.enforce(proposed_budget, current_capital, peak_capital, today_spend)

    # activate emergency stop
    engine.activate_kill_switch(reason="manual override")

    # clear after investigation
    engine.deactivate_kill_switch()
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Risk override result
# ---------------------------------------------------------------------------


@dataclass
class RiskOverride:
    """Result of a risk-engine enforcement check."""
    allowed: bool
    adjusted_budget: float
    reason: str
    triggered_cap: str = ""  # e.g. "kill_switch", "daily_spend", "drawdown"


# ---------------------------------------------------------------------------
# Global Risk Engine
# ---------------------------------------------------------------------------


class GlobalRiskEngine:
    """Thread-safe global risk guard.

    Parameters
    ----------
    max_daily_spend:
        Maximum total spend allowed per 24-hour window (USD).
    max_drawdown:
        Maximum allowed peak-to-trough capital drop (fraction, e.g. 0.30 = 30%).
    """

    def __init__(
        self,
        max_daily_spend: float = 10_000.0,
        max_drawdown: float = 0.30,
    ):
        self.max_daily_spend = max_daily_spend
        self.max_drawdown = max_drawdown

        self._lock = threading.Lock()
        self._kill_switch_active: bool = False
        self._kill_switch_reason: str = ""
        self._kill_switch_ts: float | None = None

        # Rolling daily spend tracker: list of (timestamp, amount)
        self._spend_log: list[tuple[float, float]] = []

    # ------------------------------------------------------------------
    # Kill switch
    # ------------------------------------------------------------------

    def activate_kill_switch(self, reason: str = "manual") -> None:
        """Immediately halt all new spend."""
        with self._lock:
            self._kill_switch_active = True
            self._kill_switch_reason = reason
            self._kill_switch_ts = time.time()

    def deactivate_kill_switch(self) -> None:
        """Re-enable spend after investigation."""
        with self._lock:
            self._kill_switch_active = False
            self._kill_switch_reason = ""
            self._kill_switch_ts = None

    @property
    def kill_switch_active(self) -> bool:
        with self._lock:
            return self._kill_switch_active

    # ------------------------------------------------------------------
    # Daily spend tracking
    # ------------------------------------------------------------------

    def _prune_spend_log(self, now: float) -> None:
        """Remove entries older than 24 hours (must be called under lock)."""
        cutoff = now - 86_400.0
        self._spend_log = [(t, s) for t, s in self._spend_log if t >= cutoff]

    def record_spend(self, amount: float) -> None:
        """Log *amount* as spend that occurred right now."""
        now = time.time()
        with self._lock:
            self._prune_spend_log(now)
            self._spend_log.append((now, amount))

    def today_spend(self) -> float:
        """Total spend recorded in the rolling 24-hour window."""
        now = time.time()
        with self._lock:
            self._prune_spend_log(now)
            return sum(s for _, s in self._spend_log)

    # ------------------------------------------------------------------
    # Drawdown check
    # ------------------------------------------------------------------

    def drawdown_exceeded(self, current_capital: float, peak_capital: float) -> bool:
        """Return True if current drawdown exceeds the configured threshold."""
        if peak_capital <= 0:
            return False
        drawdown = (peak_capital - current_capital) / peak_capital
        return drawdown > self.max_drawdown

    # ------------------------------------------------------------------
    # Enforcement (main entry point)
    # ------------------------------------------------------------------

    def enforce(
        self,
        proposed_budget: float,
        current_capital: float,
        peak_capital: float,
        additional_spend: float = 0.0,
    ) -> RiskOverride:
        """Gate *proposed_budget* against all risk rules.

        Parameters
        ----------
        proposed_budget:
            Budget amount the agent wishes to allocate.
        current_capital:
            Current account capital.
        peak_capital:
            Peak capital since inception (for drawdown calculation).
        additional_spend:
            Any spend that will be added on top of *proposed_budget* this cycle
            (e.g. from other agents).  Used to check the daily cap.

        Returns
        -------
        RiskOverride with the adjusted (safe) budget and reasons.
        """
        with self._lock:
            # 1. Kill switch — hard stop
            if self._kill_switch_active:
                return RiskOverride(
                    allowed=False,
                    adjusted_budget=0.0,
                    reason=f"Kill switch active: {self._kill_switch_reason}",
                    triggered_cap="kill_switch",
                )

        # 2. Drawdown check
        if self.drawdown_exceeded(current_capital, peak_capital):
            return RiskOverride(
                allowed=False,
                adjusted_budget=0.0,
                reason=(
                    f"Max drawdown exceeded: capital={current_capital:.2f}, "
                    f"peak={peak_capital:.2f}"
                ),
                triggered_cap="drawdown",
            )

        # 3. Daily spend cap
        current_daily = self.today_spend() + additional_spend
        remaining = self.max_daily_spend - current_daily
        if remaining <= 0:
            return RiskOverride(
                allowed=False,
                adjusted_budget=0.0,
                reason=f"Daily spend cap reached: {current_daily:.2f}/{self.max_daily_spend:.2f}",
                triggered_cap="daily_spend",
            )

        safe_budget = min(proposed_budget, max(0.0, remaining))
        if safe_budget < proposed_budget:
            return RiskOverride(
                allowed=True,
                adjusted_budget=safe_budget,
                reason=f"Budget capped by daily limit (remaining={remaining:.2f})",
                triggered_cap="daily_spend",
            )

        return RiskOverride(
            allowed=True,
            adjusted_budget=proposed_budget,
            reason="all_clear",
        )

    # ------------------------------------------------------------------
    # Status snapshot
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a serialisable status dict for dashboard use."""
        return {
            "kill_switch_active": self.kill_switch_active,
            "kill_switch_reason": self._kill_switch_reason,
            "max_daily_spend": self.max_daily_spend,
            "max_drawdown": self.max_drawdown,
            "today_spend": round(self.today_spend(), 2),
            "daily_spend_remaining": round(
                max(0.0, self.max_daily_spend - self.today_spend()), 2
            ),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

global_risk_engine = GlobalRiskEngine()
