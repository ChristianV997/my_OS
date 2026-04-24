import time


class PacingController:
    """Spread daily budget spend evenly over a 24-hour window."""

    def __init__(self, daily_budget: float):
        self.daily_budget = daily_budget
        self.start_time = time.time()

    def allowed_spend(self) -> float:
        elapsed = time.time() - self.start_time
        fraction_of_day = min(elapsed / 86400, 1)
        return self.daily_budget * fraction_of_day

    def should_pause(self, current_spend: float) -> bool:
        return current_spend > self.allowed_spend()
