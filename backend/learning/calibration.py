import numpy as np

class CalibrationModel:

    def __init__(self, window=100):
        self.errors = []
        self.window = window

    def update(self, predicted, actual):
        err = predicted - actual
        self.errors.append(err)
        if len(self.errors) > self.window:
            self.errors = self.errors[-self.window:]

    def stats(self):
        if len(self.errors) < 5:
            return {"bias": 0.0, "uncertainty": 1.0}
        return {
            "bias": float(np.mean(self.errors)),
            "uncertainty": float(np.std(self.errors))
        }

    def adjust_prediction(self, pred):
        s = self.stats()
        # remove bias
        corrected = pred - s["bias"]
        return corrected

    def confidence_weight(self):
        s = self.stats()
        # higher uncertainty → lower confidence
        return 1 / (1 + s["uncertainty"])


calibration_model = CalibrationModel()
