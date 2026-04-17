from backend.learning.signals import roas_velocity, roas_acceleration, advantage


def temporal_credit(state, results):
    # compute velocity/acceleration from recent history
    history = [r.get("roas", 0) for r in state.event_log.rows[-10:]]
    vel = roas_velocity(history)
    acc = roas_acceleration(history)

    enriched = []
    for r in results:
        r2 = dict(r)
        r2["velocity"] = vel
        r2["acceleration"] = acc
        enriched.append(r2)
    return enriched


def counterfactual_eval(results):
    enriched = []
    for r in results:
        pred = r.get("pred_roas", r.get("roas", 0))
        cf = pred * 0.9
        r2 = dict(r)
        r2["advantage"] = advantage(pred, cf)
        enriched.append(r2)
    return enriched


def learn(state, results):

    results = temporal_credit(state, results)
    results = counterfactual_eval(results)

    # attach signals back into event log rows for training
    for r in results:
        state.event_log.rows.append(r)

    # maintain rolling memory
    state.memory = getattr(state, "memory", []) + results
    state.memory = state.memory[-1000:]

    return state
