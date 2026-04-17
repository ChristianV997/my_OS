import time

class DelayedRewardStore:

    def __init__(self):
        self.buffer = []

    def log(self, decision, outcome):
        self.buffer.append({
            "t": time.time(),
            "decision": decision,
            "outcome": outcome
        })

    def get_ready(self, delay):
        now = time.time()
        ready = []
        for item in self.buffer:
            if now - item["t"] >= delay:
                ready.append(item)
        return ready
