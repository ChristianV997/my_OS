from core.loop import run_cycle
from core.memory import clear_memory, memory


def setup_function():
    clear_memory()


def test_run_cycle_records_event():
    run_cycle([{"spend": 10, "conversions": 1, "product": "x"}])

    assert len(memory) == 1
    event = memory[0]
    assert event["decision"]["action"] == "launch"
    assert event["result"] == "product launched"


def test_run_cycle_ignores_high_cac():
    run_cycle([{"spend": 100, "conversions": 1, "product": "x"}])

    assert len(memory) == 1
    event = memory[0]
    assert event["decision"]["action"] == "ignore"
    assert event["result"] == "noop"
