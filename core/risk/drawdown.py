class DrawdownProtector:
    """Track peak equity and halt execution when drawdown exceeds a threshold."""

    def __init__(self):
        self.peak: float = 0.0

    def update(self, equity: float) -> None:
        if equity > self.peak:
            self.peak = equity

    def drawdown(self, equity: float) -> float:
        if self.peak == 0:
            return 0.0
        return (self.peak - equity) / self.peak

    def should_stop(self, equity: float, threshold: float = 0.3) -> bool:
        return self.drawdown(equity) > threshold
