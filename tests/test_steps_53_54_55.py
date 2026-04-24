"""Tests for Steps 53, 54, 55 — system wiring, capital allocation, anomaly detection."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Step 53 — core.data.validator
# ---------------------------------------------------------------------------

class TestCampaignValidator:
    def test_valid_dict(self):
        from core.data.validator import validate_campaign
        rec = validate_campaign({"roas": 2.0, "spend": 100.0, "revenue": 200.0})
        assert rec.get("roas") == 2.0
        assert rec["spend"] == 100.0

    def test_missing_fields_filled(self):
        from core.data.validator import validate_campaign
        rec = validate_campaign({})
        assert rec.get("roas") == 0.0
        assert rec.get("spend") == 0.0

    def test_non_dict_raises(self):
        from core.data.validator import validate_campaign
        with pytest.raises(ValueError):
            validate_campaign("not a dict")  # type: ignore

    def test_dict_method(self):
        from core.data.validator import validate_campaign
        rec = validate_campaign({"roas": 1.5})
        d = rec.dict()
        assert isinstance(d, dict)
        assert d["roas"] == 1.5


# ---------------------------------------------------------------------------
# Step 53 — core.copilot
# ---------------------------------------------------------------------------

class TestCopilotWhatif:
    def test_spend_scaling(self):
        from core.copilot.whatif import what_if
        state = {"spend": 100.0, "revenue": 200.0, "roas": 2.0}
        projected = what_if(state, {"spend": 200.0})
        assert projected["spend"] == 200.0
        assert projected["roas"] == pytest.approx(2.0, rel=0.01)

    def test_no_mutation(self):
        from core.copilot.whatif import what_if
        state = {"spend": 100.0, "revenue": 200.0}
        what_if(state, {"spend": 150.0})
        assert state["spend"] == 100.0  # original unchanged


class TestCopilotScenario:
    def test_returns_best_and_scenarios(self):
        from core.copilot.scenario import run_scenarios
        state = {"spend": 100.0, "revenue": 200.0, "roas": 2.0}
        result = run_scenarios(state)
        assert "best" in result
        assert "scenarios" in result
        assert isinstance(result["scenarios"], list)
        assert len(result["scenarios"]) > 0


class TestCopilotOptimizer:
    def test_scale_on_high_roas(self):
        from core.copilot.optimizer import decide
        result = decide({"best": {"roas": 3.0}, "multiplier": 1.5})
        assert result == "SCALE"

    def test_kill_on_low_roas(self):
        from core.copilot.optimizer import decide
        result = decide({"best": {"roas": 0.5}, "multiplier": 1.0})
        assert result == "KILL"


# ---------------------------------------------------------------------------
# Step 53 — core.rl
# ---------------------------------------------------------------------------

class TestPolicyNet:
    def test_select_action_returns_valid(self):
        from core.rl.policy import PolicyNet, ACTIONS
        policy = PolicyNet()
        action = policy.select_action({"roas": 2.0})
        assert action in ACTIONS

    def test_update_does_not_crash(self):
        from core.rl.policy import PolicyNet
        policy = PolicyNet()
        policy.update("SCALE", 1.5)  # should not raise


class TestReplayBuffer:
    def test_add_and_sample(self):
        from core.rl.replay_buffer import ReplayBuffer
        buf = ReplayBuffer(capacity=100)
        buf.add({"state": {"roas": 1.0}, "action": "HOLD", "reward": 1.0})
        assert len(buf) == 1
        samples = buf.sample(1)
        assert len(samples) == 1

    def test_sample_empty(self):
        from core.rl.replay_buffer import ReplayBuffer
        buf = ReplayBuffer(capacity=100)
        assert buf.sample(5) == []


# ---------------------------------------------------------------------------
# Step 53 — core.risk.guard
# ---------------------------------------------------------------------------

class TestRiskGuard:
    def test_returns_action_normally(self):
        from core.risk.guard import enforce
        action = enforce("SCALE", {"spend": 10.0, "revenue": 100.0})
        assert isinstance(action, str)

    def test_returns_string(self):
        from core.risk.guard import enforce
        result = enforce("BUY", {"spend": 0.0, "revenue": 0.0})
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Step 53 — core.engine.execution_loop
# ---------------------------------------------------------------------------

class TestExecutionLoop:
    def test_basic_cycle(self):
        from core.engine.execution_loop import execution_step
        result = execution_step({"roas": 1.5, "spend": 100.0, "revenue": 150.0})
        assert "action" in result
        assert "state" in result

    def test_action_is_string(self):
        from core.engine.execution_loop import execution_step
        result = execution_step({"roas": 2.5, "spend": 200.0, "revenue": 500.0})
        assert isinstance(result["action"], str)


# ---------------------------------------------------------------------------
# Step 54 — core.capital.allocator
# ---------------------------------------------------------------------------

class TestCapitalAllocator:
    def test_allocate_sums_to_budget(self):
        from core.capital.allocator import allocate
        strategies = [
            {"roas": 2.0, "profit": 100.0, "drawdown": 0.1},
            {"roas": 1.5, "profit": 50.0, "drawdown": 0.05},
            {"roas": 0.9, "profit": -10.0, "drawdown": 0.2},
        ]
        allocations = allocate(strategies, total_budget=1000.0)
        assert len(allocations) == 3
        assert sum(allocations) == pytest.approx(1000.0, rel=0.01)

    def test_allocate_respects_max_frac(self):
        from core.capital.allocator import allocate
        strategies = [
            {"roas": 5.0, "profit": 500.0, "drawdown": 0.0},
            {"roas": 0.1, "profit": -100.0, "drawdown": 0.9},
        ]
        allocations = allocate(strategies, total_budget=1000.0)
        assert max(allocations) <= 1000.0 * 0.35 + 1.0  # tolerance

    def test_allocate_empty(self):
        from core.capital.allocator import allocate
        assert allocate([], 1000.0) == []

    def test_allocate_single(self):
        from core.capital.allocator import allocate
        assert allocate([{"roas": 2.0}], 1000.0) == [1000.0]

    def test_scale_budget_high_roas(self):
        from core.capital.allocator import scale_budget
        assert scale_budget(100.0, 2.6) == pytest.approx(130.0)

    def test_scale_budget_kill(self):
        from core.capital.allocator import scale_budget
        assert scale_budget(100.0, 0.5) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Step 55 — core.anomaly
# ---------------------------------------------------------------------------

class TestAnomalyFeatures:
    def test_feature_length(self):
        from core.anomaly.features import build_features, _FEATURE_KEYS
        state = {"roas": 2.0, "ctr": 0.05, "cvr": 0.02, "spend": 100.0, "revenue": 200.0}
        features = build_features(state)
        assert len(features) == len(_FEATURE_KEYS)

    def test_missing_keys_default_zero(self):
        from core.anomaly.features import build_features
        features = build_features({})
        assert all(f == 0.0 for f in features)


class TestAnomalyModel:
    def test_score_returns_float(self):
        from core.anomaly.model import AnomalyModel
        model = AnomalyModel()
        score = model.score([1.0, 0.05, 0.02, 100.0, 200.0])
        assert isinstance(score, float)

    def test_is_anomaly_bool(self):
        from core.anomaly.model import AnomalyModel
        model = AnomalyModel()
        result = model.is_anomaly([1.0, 0.05, 0.02, 100.0, 200.0])
        assert isinstance(result, bool)

    def test_fit_with_data(self):
        from core.anomaly.model import AnomalyModel
        import random
        model = AnomalyModel()
        X = [[random.random() for _ in range(5)] for _ in range(20)]
        model.fit(X)  # should not raise


class TestAnomalyDetector:
    def test_detect_returns_bool(self):
        from core.anomaly.detector import detect
        result = detect({"roas": 2.0, "ctr": 0.05, "cvr": 0.02, "spend": 100.0, "revenue": 200.0})
        assert isinstance(result, bool)


class TestAnomalyResponse:
    def test_kill_on_very_low_roas(self):
        from core.anomaly.response import respond
        assert respond({"roas": 0.5}) == "KILL"

    def test_throttle_on_low_roas(self):
        from core.anomaly.response import respond
        assert respond({"roas": 1.0}) == "THROTTLE"

    def test_none_on_normal_roas(self):
        from core.anomaly.response import respond
        assert respond({"roas": 2.5}) == "NONE"
