from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight
from backend.learning.calibration import calibration_model
from backend.agents.strategies import strategies
from backend.agents.allocator import allocator
from agents.world_model import world_model


def decide(state):

    world_model.train(state.event_log)

    history=[r.get("roas",0) for r in state.event_log.rows[-10:]]
    vel=roas_velocity(history)
    acc=roas_acceleration(history)

    decisions=[]

    total_budget = 10

    for name, strat in strategies.items():

        n_actions = allocator.allocate(name, total_budget)
        proposals = strat.propose(state)[:n_actions]

        for action in proposals:

            preds=world_model.predict(action)

            weighted_pred = (
                0.5*preds["roas_6h"] +
                0.3*preds["roas_12h"] +
                0.2*preds["roas_24h"]
            )

            corrected_pred = calibration_model.adjust_prediction(weighted_pred)

            c_score=causal_score(action,state.graph)
            velocity_bonus=vel+acc
            bandit_w=bandit_weight(action,state.graph)

            confidence = calibration_model.confidence_weight()

            score = (corrected_pred + c_score + velocity_bonus + bandit_w) * confidence

            decisions.append({
                "action":action,
                "score":score,
                "pred": corrected_pred,
                "strategy": name
            })

    decisions.sort(key=lambda x:x["score"],reverse=True)

    return decisions
