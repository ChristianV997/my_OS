import time
from collections import deque

class HealthDashboard:
    def __init__(self, window=50):
        self.roas = deque(maxlen=window)
        self.pred_error = deque(maxlen=window)
        self.improvement = deque(maxlen=window)
        self.novelty_weight = 0.0
        self.strategy_count = 0
        self.diversity = 0.0

    def update(self, roas, pred, actual, novelty_weight, strategy_count, diversity):
        error = pred - actual
        self.roas.append(roas)
        self.pred_error.append(error)

        if len(self.roas) > 1:
            self.improvement.append(self.roas[-1] - self.roas[-2])

        self.novelty_weight = novelty_weight
        self.strategy_count = strategy_count
        self.diversity = diversity

    def summary(self):
        avg_roas = sum(self.roas)/len(self.roas) if self.roas else 0
        avg_err = sum(self.pred_error)/len(self.pred_error) if self.pred_error else 0
        imp = sum(self.improvement)/len(self.improvement) if self.improvement else 0

        return {
            "avg_roas": round(avg_roas, 4),
            "prediction_error": round(avg_err, 4),
            "improvement_rate": round(imp, 4),
            "novelty_weight": round(self.novelty_weight, 4),
            "strategy_count": self.strategy_count,
            "diversity": round(self.diversity, 4)
        }

    def alerts(self):
        alerts = []

        if self.improvement and sum(self.improvement)/len(self.improvement) < 0:
            alerts.append("⚠️ Learning stalled")

        if self.diversity < 0.1:
            alerts.append("⚠️ Diversity collapse")

        if self.pred_error and abs(sum(self.pred_error)/len(self.pred_error)) > 0.5:
            alerts.append("⚠️ Prediction error high")

        return alerts

    def display(self):
        s = self.summary()
        print("\n=== SYSTEM HEALTH ===")
        for k, v in s.items():
            print(f"{k}: {v}")

        for a in self.alerts():
            print(a)


# simple loop runner
if __name__ == "__main__":
    dash = HealthDashboard()

    # mock loop (replace with real hooks)
    import random
    for _ in range(100):
        roas = random.uniform(0.5, 3.0)
        pred = roas + random.uniform(-0.3, 0.3)
        dash.update(
            roas=roas,
            pred=pred,
            actual=roas,
            novelty_weight=random.uniform(0.1, 0.8),
            strategy_count=random.randint(2, 6),
            diversity=random.uniform(0.05, 0.5)
        )
        dash.display()
        time.sleep(0.2)
