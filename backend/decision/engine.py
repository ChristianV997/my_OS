import random

from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight
from agents.world_model import world_model


def decide(state):

    world_model.train(state.event_log)

    history=[r.get("roas",0) for r in state.event_log.rows[-10:]]
    vel=roas_velocity(history)
    acc=roas_acceleration(history)

    decisions=[]

    for _ in range(5):

        action={"variant":random.randint(1,5)}

        preds=world_model.predict(action)

        weighted_pred = (
            0.5*preds["roas_6h"] +
            0.3*preds["roas_12h"] +
            0.2*preds["roas_24h"]
        )

        c_score=causal_score(action,state.graph)
        velocity_bonus=vel+acc
        bandit_w=bandit_weight(action,state.graph)

        score = weighted_pred + c_score + velocity_bonus + bandit_w

        decisions.append({"action":action,"score":score})

    decisions.sort(key=lambda x:x["score"],reverse=True)

    return decisions
