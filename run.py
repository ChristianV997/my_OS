import time

from core.loop import run_cycle


def run_forever(interval_seconds=300):
    while True:
        signals = [{"product": "test", "spend": 10, "conversions": 1}]
        run_cycle(signals)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_forever()
