import time

from tasks.discovery import run_discovery


class FullLoop:
    def run(self, iterations=None, sleep_seconds=0):
        count = 0

        while iterations is None or count < iterations:
            run_discovery.delay()
            count += 1
            if sleep_seconds:
                time.sleep(sleep_seconds)

        return count
