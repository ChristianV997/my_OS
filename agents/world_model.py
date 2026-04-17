import numpy as np

class WorldModel:

    def __init__(self):
        self.weights = None

    def featurize(self, action, context=None):
        # simple numeric encoding
        vec = []
        for v in action.values():
            try:
                vec.append(float(v))
            except:
                vec.append(0.0)
        return np.array(vec)

    def train(self, event_log):

        if len(event_log.rows) < 10:
            return

        X = []
        y = []

        for r in event_log.rows:
            action = {"variant": r.get("variant", 0)}
            X.append(self.featurize(action))
            y.append(r.get("roas", 0))

        X = np.array(X)
        y = np.array(y)

        try:
            self.weights = np.linalg.lstsq(X, y, rcond=None)[0]
        except:
            self.weights = None

    def predict(self, action):

        if self.weights is None:
            return 1.0

        x = self.featurize(action)

        try:
            return float(np.dot(x, self.weights))
        except:
            return 1.0


world_model = WorldModel()
