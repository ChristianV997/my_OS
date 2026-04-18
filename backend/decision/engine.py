from backend.decision.scoring import causal_score
from backend.learning.signals import roas_velocity, roas_acceleration
from backend.learning.bandit_update import bandit_weight
from backend.learning.calibration import calibration_model
from backend.learning.campaign_learning import campaign_learning
from backend.agents.campaign_budget import campaign_budget_allocator
from backend.agents.structural_evolution import structural_engine
from backend.agents.strategies import strategies
from backend.agents.allocator import allocator
from agents.world_model import world_model

import random

CAMPAIGN_WEIGHT = 0.5
BUDGET_WEIGHT = 0.3


def decide(state):

    if not structural_engine.population:
        structural_engine.initialize()

    structure = random.choice(structural_engine.population)

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

            c_score = causal_score(action,state.graph) if structure["features"]["use_causal"] else 0
            velocity_bonus = (vel+acc) if structure["features"]["use_velocity"] else 0

            campaign_id = action.get("campaign_id")
            campaign_score = campaign_learning.score(campaign_id)
            budget_score = campaign_budget_allocator.get_budget(campaign_id)

            bandit_w=bandit_weight((name, campaign_id),state.graph)

            confidence = calibration_model.confidence_weight()

            weights = structure["weights"]

            score = (
                weights["world_model"] * corrected_pred +
                weights["causal"] * c_score +
                weights["velocity"] * velocity_bonus +
                weights["advantage"] * bandit_w
            ) * confidence

            score += CAMPAIGN_WEIGHT * campaign_score
            score += BUDGET_WEIGHT * budget_score

            decisions.append({
                "action":action,
                "score":score,
                "pred": corrected_pred,
                "strategy": name,
                "campaign_id": campaign_id,
                "structure": structure
            })

    decisions.sort(key=lambda x:x["score"],reverse=True)

    return decisions
