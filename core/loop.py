from agents.execution_agent import execute
from core.cac import estimate_cac
from core.memory import store_event

# Launch offers only when estimated CAC is below 20 cost-units per conversion.
CAC_LAUNCH_THRESHOLD = 20


def run_cycle(signals):
    for signal in signals or []:
        score = estimate_cac([signal])

        decision = {
            "action": "launch" if score < CAC_LAUNCH_THRESHOLD else "ignore",
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
