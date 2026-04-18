import numpy as np
from sklearn.linear_model import Ridge


class WorldModel:

    HORIZONS = ["6h", "12h", "24h"]

    def __init__(self):
        self._models = {}
        self._fitted = set()

    def _featurize(self, action):
        return np.array([float(v) for v in action.values()], dtype=float)

    def train(self, event_log):
        rows = event_log.rows
        if len(rows) < 20:
            return

        features, targets = [], {h: [] for h in self.HORIZONS}
        for r in rows:
            action = {"variant": r.get("variant", 0)}
            features.append(self._featurize(action))
            base = r.get("roas", 0)
            targets["6h"].append(r.get("roas_6h", base))
            targets["12h"].append(r.get("roas_12h", base))
            targets["24h"].append(r.get("roas_24h", base))

        X = np.array(features)
        for h, y in targets.items():
            m = Ridge(alpha=1.0)
            m.fit(X, np.array(y))
            self._models[h] = m
            self._fitted.add(h)

    def predict(self, action):
        x = self._featurize(action).reshape(1, -1)
        return {
            f"roas_{h}": float(self._models[h].predict(x)[0])
            if h in self._fitted else 1.0
            for h in self.HORIZONS
        }


world_model = WorldModel()
