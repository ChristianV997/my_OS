import random

from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration, advantage


def decide(state):

    history = [r.get("roas", 0) for r in state.event_log.rows[-10:]]

    vel = roas_velocity(history)
    acc = roas_acceleration(history)

    decisions = []

    for _ in range(5):

        action = {"variant": random.randint(1, 5)}

        world_pred = random.uniform(0.5, 2.0)

        c_score = causal_score(action, state.graph)

        velocity_bonus = vel + acc

        # placeholder counterfactual baseline
        cf = world_pred * 0.9
        adv = advantage(world_pred, cf)

        score = world_pred + c_score + velocity_bonus + adv

        decisions.append({
            "action": action,
            "score": score,
            "meta": {
                "world": world_pred,
                "causal": c_score,
                "velocity": vel,
                "acceleration": acc,
                "advantage": adv
            }
        })

    decisions.sort(key=lambda x: x["score"], reverse=True)

    return decisions
