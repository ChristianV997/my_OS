class CalibrationLog:

    def __init__(self):
        self.history = []

    def log(self, stats):
        self.history.append(stats)
        if len(self.history) > 500:
            self.history = self.history[-500:]

    def trend_bias(self):
        if len(self.history) < 5:
            return 0
        return sum(x['bias'] for x in self.history[-5:]) / 5

    def trend_uncertainty(self):
        if len(self.history) < 5:
            return 1
        return sum(x['uncertainty'] for x in self.history[-5:]) / 5

calibration_log = CalibrationLog()
