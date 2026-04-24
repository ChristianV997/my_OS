weights = {
    "margin": 0.5,
    "competition": -0.5,
}

history = []


def update_weights(signal, outcome):
    global weights

    reward = 1 if outcome == "scale" else -1

    margin = signal.get("estimated_margin", 0)
    competition = signal.get("competition", 0)

    weights["margin"] += 0.01 * reward * margin
    weights["competition"] += 0.01 * reward * (-competition)

    history.append({
        "signal": signal,
        "outcome": outcome,
        "weights": weights.copy(),
    })


def score(signal):
    return (
        signal.get("estimated_margin", 0) * weights["margin"]
        + signal.get("competition", 0) * weights["competition"]
    )
