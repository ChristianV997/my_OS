class EventLog:

    MAX_ROWS = 10_000

    def __init__(self):
        self.rows = []

    def log_batch(self, results):
        self.rows.extend(results)
        if len(self.rows) > self.MAX_ROWS:
            self.rows = self.rows[-self.MAX_ROWS:]
