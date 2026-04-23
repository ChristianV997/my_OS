import time

from core.loop import run_cycle

DEFAULT_CYCLE_INTERVAL_SECONDS = 300


def default_signal_provider():
    return [{"product": "test", "spend": 10, "conversions": 1}]


def run_forever(interval_seconds=DEFAULT_CYCLE_INTERVAL_SECONDS, signal_provider=default_signal_provider):
    while True:
        run_cycle(signal_provider())
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_forever()
