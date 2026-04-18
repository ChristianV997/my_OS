from backend.learning.signals import roas_velocity, roas_acceleration, advantage


def temporal_credit(state, results):
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

    # enrich the rows already in event_log (added by log_batch) in-place
    for row, enriched in zip(state.event_log.rows[-len(results):], results):
        row.update(enriched)

    state.memory = (state.memory + results)[-1000:]

    return state
