from agents.execution_agent import execute
from core.cac import estimate_cac
from core.memory import store_event


def run_cycle(signals):
    for signal in signals or []:
        score = estimate_cac([signal])

        decision = {
            "action": "launch" if score < 20 else "ignore",
        }

        result = execute(decision)

        store_event(
            {
                "signal": signal,
                "score": score,
                "decision": decision,
                "result": result,
            }
        )
