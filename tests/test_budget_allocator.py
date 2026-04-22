"""Tests for CVXPY risk-adjusted budget allocator."""
import pytest
from backend.decision.budget_allocator import (
    allocate,
    allocation_summary,
    DEFAULT_TOTAL_BUDGET,
    DEFAULT_MIN_FRAC,
    DEFAULT_MAX_FRAC,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _decisions(preds, widths=None):
    if widths is None:
        widths = [0.3] * len(preds)
    return [{"action": {"variant": i + 1}, "pred": p, "pred_width": w}
            for i, (p, w) in enumerate(zip(preds, widths))]


# ── edge cases ────────────────────────────────────────────────────────────────

def test_empty_decisions_returns_empty():
    assert allocate([]) == []


def test_single_decision_gets_full_budget():
    result = allocate([{"action": {}, "pred": 1.2, "pred_width": 0.3}])
    assert len(result) == 1
    assert abs(result[0] - DEFAULT_TOTAL_BUDGET) < 1e-6


# ── constraint satisfaction ───────────────────────────────────────────────────

class TestConstraints:
    def test_total_sums_to_budget(self):
        decisions = _decisions([1.5, 1.2, 0.8, 1.0, 0.9])
        budgets = allocate(decisions)
        assert abs(sum(budgets) - DEFAULT_TOTAL_BUDGET) < 1e-4

    def test_total_sums_with_custom_budget(self):
        decisions = _decisions([1.0, 1.1, 0.9, 1.3, 0.7])
        total = 1000.0
        budgets = allocate(decisions, total_budget=total)
        assert abs(sum(budgets) - total) < 1e-4

    def test_min_fraction_respected(self):
        decisions = _decisions([2.0, 0.1, 0.1, 0.1, 0.1])
        budgets = allocate(decisions)
        lo = DEFAULT_MIN_FRAC * DEFAULT_TOTAL_BUDGET
        for b in budgets:
            assert b >= lo - 1e-4

    def test_max_fraction_respected(self):
        decisions = _decisions([5.0, 0.1, 0.1, 0.1, 0.1])
        budgets = allocate(decisions)
        hi = DEFAULT_MAX_FRAC * DEFAULT_TOTAL_BUDGET
        for b in budgets:
            assert b <= hi + 1e-4

    def test_returns_n_values(self):
        for n in (2, 3, 5, 7):
            decisions = _decisions([1.0] * n)
            budgets = allocate(decisions)
            assert len(budgets) == n


# ── optimality behaviour ─────────────────────────────────────────────────────

class TestOptimality:
    def test_higher_pred_gets_more_budget(self):
        """With equal widths, higher pred should attract more budget."""
        decisions = _decisions([2.0, 0.5], widths=[0.1, 0.1])
        budgets = allocate(decisions)
        assert budgets[0] > budgets[1]

    def test_lower_width_gets_more_budget(self):
        """With equal preds, lower (more certain) width should attract more budget."""
        decisions = _decisions([1.5, 1.5], widths=[0.1, 1.5])
        budgets = allocate(decisions)
        assert budgets[0] > budgets[1]

    def test_uniform_when_preds_equal_and_widths_equal(self):
        """Identical decisions → degenerate LP; any feasible split is valid."""
        n = 5
        decisions = _decisions([1.0] * n, widths=[0.2] * n)
        budgets = allocate(decisions)
        # All constraints must still be satisfied
        lo = DEFAULT_MIN_FRAC * DEFAULT_TOTAL_BUDGET
        hi = DEFAULT_MAX_FRAC * DEFAULT_TOTAL_BUDGET
        assert abs(sum(budgets) - DEFAULT_TOTAL_BUDGET) < 1e-4
        for b in budgets:
            assert lo - 1e-4 <= b <= hi + 1e-4

    def test_risk_lambda_zero_ignores_width(self):
        """With risk_lambda=0, width has no effect — only pred matters."""
        decisions = _decisions([1.5, 0.5], widths=[10.0, 0.0])
        budgets = allocate(decisions, risk_lambda=0.0)
        assert budgets[0] > budgets[1]


# ── fallback behaviour ────────────────────────────────────────────────────────

class TestFallback:
    def test_fallback_to_uniform_when_all_coeff_nonpositive(self):
        """All preds very low + high risk_lambda → all coefficients ≤ 0 → uniform."""
        decisions = _decisions([0.05, 0.05, 0.05], widths=[5.0, 5.0, 5.0])
        budgets = allocate(decisions, risk_lambda=1.0)
        expected = DEFAULT_TOTAL_BUDGET / 3
        for b in budgets:
            assert abs(b - expected) < 1e-3

    def test_missing_pred_width_defaults_gracefully(self):
        """Decisions without pred_width should use the 0.5 default."""
        decisions = [{"action": {"variant": i}, "pred": 1.0} for i in range(3)]
        budgets = allocate(decisions)
        assert len(budgets) == 3
        assert abs(sum(budgets) - DEFAULT_TOTAL_BUDGET) < 1e-4


# ── allocation_summary ────────────────────────────────────────────────────────

def test_allocation_summary_is_string():
    decisions = _decisions([1.2, 0.9, 1.5])
    budgets = allocate(decisions)
    s = allocation_summary(decisions, budgets)
    assert isinstance(s, str)
    assert "budget:" in s


def test_allocation_summary_contains_variant_and_amount():
    decisions = _decisions([1.0, 1.0])
    budgets = [200.0, 300.0]
    s = allocation_summary(decisions, budgets)
    assert "$200" in s
    assert "$300" in s
