import json

TRACE_PATH = "backend/monitoring/decision_trace.jsonl"


def print_last_decision_traces(n=10):
    try:
        with open(TRACE_PATH, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("No decision trace file found")
        return

    print("\n--- ROOT CAUSE TRACE (LAST {} DECISIONS) ---".format(n))

    for line in lines[-n:]:
        try:
            entry = json.loads(line.strip())
            print({
                "world_model": entry.get("world_model_score"),
                "causal": entry.get("causal_score"),
                "velocity": entry.get("velocity_bonus"),
                "advantage": entry.get("advantage"),
                "confidence": entry.get("confidence"),
                "final": entry.get("final_score"),
                "contrib": entry.get("contributions")
            })
        except Exception as e:
            print("Error parsing line:", e)
