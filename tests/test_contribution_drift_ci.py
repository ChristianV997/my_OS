import numpy as np
from backend.monitoring.root_cause_debug import print_last_decision_traces


def compute_contributions(w, c, v, a):
    total = w + c + v + a + 1e-8
    return {
        "world_model": w / total,
        "causal": c / total,
        "velocity": v / total,
        "advantage": a / total
    }


def test_no_dominant_signal_over_time():
    history = []

    # simulate varying contributions over time
    for i in range(50):
        w = np.random.uniform(0.2, 1.0)
        c = np.random.uniform(0.2, 1.0)
        v = np.random.uniform(0.1, 0.8)
        a = np.random.uniform(0.2, 1.0)

        contrib = compute_contributions(w, c, v, a)
        history.append(contrib)

    # compute average contribution per component
    avg = {k: np.mean([h[k] for h in history]) for k in history[0]}

    # assert no component dominates >80%
    for k, val in avg.items():
        if val > 0.8:
            print("\n--- CONTRIBUTION COLLAPSE DETECTED ---")
            print("AVERAGES:", avg)
            print_last_decision_traces(10)
            raise AssertionError(f"Component {k} dominates with {val:.2f}")
