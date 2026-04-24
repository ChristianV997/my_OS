import numpy as np


class Policy:
    """Simple linear policy gradient for online RL."""

    def __init__(self, n):
        self.w = np.zeros(n)

    def predict(self, x):
        return float(np.dot(self.w, x))

    def update(self, x, r, lr=0.01):
        pred = self.predict(x)
        err = r - pred
        self.w += lr * err * x

    def save(self, save_fn):
        save_fn("policy", {"w": self.w.tolist()})

    def load(self, load_fn):
        data = load_fn("policy", None)
        if data:
            self.w = np.array(data["w"])
