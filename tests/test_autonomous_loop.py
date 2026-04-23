from agents.execution_agent import execute
from core.loop import run_cycle
from core.memory import clear_memory, memory


def setup_function():
    clear_memory()


def test_run_cycle_records_event():
    run_cycle([{"spend": 10, "conversions": 1, "product": "x"}])

    assert len(memory) == 1
    event = memory[0]
    assert event["score"] == 10
    assert event["decision"]["action"] == "launch"
    assert event["result"] == "product launched"


def test_run_cycle_ignores_high_cac():
    run_cycle([{"spend": 100, "conversions": 1, "product": "x"}])

    assert len(memory) == 1
    event = memory[0]
    assert event["score"] == 100
    assert event["decision"]["action"] == "ignore"
    assert event["result"] == "noop"


def test_execute_supports_scale_and_kill_actions():
    assert execute({"action": "scale"}) == "budget increased"
    assert execute({"action": "kill"}) == "campaign stopped"
