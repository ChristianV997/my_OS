import numpy as np


class LinUCB:
    """Contextual bandit using LinUCB (disjoint model)."""

    def __init__(self, n_features, arms, alpha=1.0):
        self.arms = arms
        self.alpha = alpha
        self.A = {a: np.eye(n_features) for a in arms}
        self.b = {a: np.zeros((n_features, 1)) for a in arms}

    def choose(self, x):
        x = np.asarray(x).reshape(-1, 1)
        best_arm = None
        best_score = -1e9

        for a in self.arms:
            A_inv = np.linalg.inv(self.A[a])
            theta = A_inv @ self.b[a]
            ucb = float((theta.T @ x).item()) + self.alpha * float(np.sqrt((x.T @ A_inv @ x).item()))

            if ucb > best_score:
                best_score = ucb
                best_arm = a

        return best_arm

    def update(self, arm, x, reward):
        x = np.asarray(x).reshape(-1, 1)
        self.A[arm] += x @ x.T
        self.b[arm] += reward * x

    def save_state(self, save_fn):
        data = {
            arm: {
                "A": self.A[arm].tolist(),
                "b": self.b[arm].tolist(),
            }
            for arm in self.arms
        }
        save_fn("bandit", data)

    def load_state(self, load_fn):
        data = load_fn("bandit", {})
        for arm in data:
            if arm in self.A:
                self.A[arm] = np.array(data[arm]["A"])
                self.b[arm] = np.array(data[arm]["b"])
