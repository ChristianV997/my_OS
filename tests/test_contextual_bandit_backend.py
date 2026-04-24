"""Tests for backend/learning/contextual_bandit.py (LinUCB wiring)"""
import backend.learning.contextual_bandit as cb
from backend.core.state import SystemState


def test_select_arm_returns_valid_arm():
    state = SystemState()
    arm = cb.select_arm(state)
    assert arm in cb._ARMS


def test_record_reward_does_not_raise():
    state = SystemState()
    arm = cb.select_arm(state)
    cb.record_reward(arm, state, 1.5)


def test_bandit_instance_has_arms():
    b = cb.bandit_instance()
    assert b.arms == cb._ARMS


def test_multiple_cycles_update_bandit():
    """b vectors are updated when features are non-zero (e.g. non-default capital)."""
    from backend.core.state import SystemState

    state = SystemState()
    state.capital = 1500.0  # non-default capital → non-zero capital feature

    for _ in range(5):
        arm = cb.select_arm(state)
        cb.record_reward(arm, state, 2.0)

    # After updates b vectors should have been modified for at least one arm
    b_obj = cb.bandit_instance()
    any_nonzero = any(b_obj.b[a].any() for a in b_obj.arms)
    assert any_nonzero


def test_encode_context_length():
    state = SystemState()
    ctx = cb._encode_context(state)
    assert len(ctx) == cb._N_FEATURES


def test_encode_context_all_floats():
    state = SystemState()
    ctx = cb._encode_context(state)
    for v in ctx:
        assert isinstance(v, float)
