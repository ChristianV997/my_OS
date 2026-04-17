from core.state import SystemState
from execution.loop import run_cycle


def main():
    state = SystemState()
    while True:
        state = run_cycle(state)


if __name__ == "__main__":
    main()
