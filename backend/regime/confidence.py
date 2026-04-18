class RegimeConfidence:

    def __init__(self, window=50):
        self.history = []
        self.window = window

    def update(self, detected, true):
        correct = int(detected == true)
        self.history.append(correct)
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]

    def confidence(self):
        if len(self.history) < 5:
            return 0.5
        return sum(self.history) / len(self.history)


regime_confidence = RegimeConfidence()
