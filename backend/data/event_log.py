class EventLog:

    def __init__(self):
        self.rows = []

    def log_batch(self, results):
        self.rows.extend(results)
