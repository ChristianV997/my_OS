import numpy as np
from backend.simulation.reality_gap import RealityGapEngine


def gen_stable(n=60):
    base = np.ones(n) * 1.5
    noise = np.random.normal(0, 0.05, n)
    return base + noise


def gen_volatile(n=60):
    base = np.ones(n) * 1.5
    noise = np.random.normal(0, 0.3, n)
    return base + noise


def gen_regime_shift(n=60):
    first = np.ones(n//2) * 1.2
    second = np.ones(n - n//2) * 2.0
    series = np.concatenate([first, second])
    noise = np.random.normal(0, 0.1, n)
    return series + noise


def run_test(sim_series, real_series):
    engine = RealityGapEngine(window=50)
    gaps = []
    params = []

    for s, r in zip(sim_series, real_series):
        gap = engine.update(s, r)
        engine.tune()
        if gap is not None:
            gaps.append(gap)
            params.append(engine.params.copy())

    return gaps, params


def assert_convergence(gaps, params):
    assert len(gaps) > 20

    first = np.mean(gaps[:10])
    last = np.mean(gaps[-10:])

    # convergence or stability
    assert last <= first + 0.25, "Reality gap not converging"

    # parameter stability
    noise_vals = [p['noise_scale'] for p in params]
    assert np.var(noise_vals) < 0.15, "Parameter instability detected"


def test_stable_regime():
    real = gen_stable()
    sim = real + np.random.normal(0.2, 0.1, len(real))
    gaps, params = run_test(sim, real)
    assert_convergence(gaps, params)


def test_volatile_regime():
    real = gen_volatile()
    sim = real + np.random.normal(0.3, 0.2, len(real))
    gaps, params = run_test(sim, real)
    assert_convergence(gaps, params)


def test_regime_shift():
    real = gen_regime_shift()
    sim = real + np.random.normal(0.25, 0.15, len(real))
    gaps, params = run_test(sim, real)
    assert_convergence(gaps, params)
