def execute(decisions, state):
    results = []
    for d in decisions:
        results.append({"roas":1.2,"revenue":100,"cost":80})
    return results


from backend.decision.engine import decide


def run_cycle(state):

    decisions = decide(state)

    results = execute(decisions, state)

    state.event_log.log_batch(results)

    return state
