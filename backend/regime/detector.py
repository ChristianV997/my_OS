import numpy as np

class RegimeDetector:

    def __init__(self, window=30):
        self.window = window

    def detect(self, event_log):

        rows = event_log.rows[-self.window:]

        if len(rows) < 10:
            return "unknown"

        roas = np.array([r.get("roas", 0) for r in rows])

        # variance
        var = np.var(roas)

        # trend (slope)
        x = np.arange(len(roas))
        slope = np.polyfit(x, roas, 1)[0]

        # volatility spikes
        diffs = np.diff(roas)
        volatility = np.std(diffs)

        # classification
        if var < 0.02 and abs(slope) < 0.01:
            return "stable"

        if slope > 0.02:
            return "growth"

        if slope < -0.02:
            return "decay"

        if volatility > 0.1:
            return "volatile"

        return "neutral"


detector = RegimeDetector()
