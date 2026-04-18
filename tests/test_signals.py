from backend.learning.signals import roas_velocity, roas_acceleration, advantage


def test_velocity_insufficient_history():
    assert roas_velocity([]) == 0
    assert roas_velocity([1.0]) == 0


def test_velocity():
    assert roas_velocity([1.0, 1.5]) == 0.5
    assert roas_velocity([2.0, 1.0]) == -1.0


def test_acceleration_insufficient_history():
    assert roas_acceleration([1.0, 2.0]) == 0


def test_acceleration():
    assert roas_acceleration([1.0, 2.0, 4.0]) == 1.0
    assert roas_acceleration([4.0, 2.0, 1.0]) == 1.0


def test_advantage():
    assert abs(advantage(1.5, 1.0) - 0.5) < 1e-9
    assert abs(advantage(0.8, 1.0) - (-0.2)) < 1e-9
