from dataclasses import dataclass
from typing import Dict, List

from core.risk_rules import RiskRules, RiskDecision


@dataclass
class BudgetPlan:
    campaign_id: str
    action: str
    reason: str
    current_budget: float
    new_budget: float


class BudgetAllocator:
    """Allocate daily budgets across campaigns based on ROAS and risk rules."""

    def __init__(
        self,
        risk_rules: RiskRules,
        max_daily_budget: float = 50.0,
        max_total_increase_per_day: float = 0.30,
        min_budget: float = 5.0,
        max_campaign_share: float = 0.35,
    ):
        self.risk_rules = risk_rules
        self.max_daily_budget = max_daily_budget
        self.max_total_increase_per_day = max_total_increase_per_day
        self.min_budget = min_budget
        self.max_campaign_share = max_campaign_share

    def allocate(
        self,
        campaign_stats: Dict[str, Dict],
        current_budget_map: Dict[str, float],
        current_total_daily_budget: float,
        peak_equity: float,
        current_equity: float,
    ) -> List[BudgetPlan]:
        plans: List[BudgetPlan] = []

        if self.risk_rules.should_stop_for_drawdown(current_equity, peak_equity):
            for cid, current_budget in current_budget_map.items():
                plans.append(
                    BudgetPlan(cid, "kill", "max_drawdown_hit", current_budget, 0.0)
                )
            return plans

        proposed_total = 0.0

        for cid, stats in campaign_stats.items():
            current_budget = float(current_budget_map.get(cid, self.min_budget))
            roas = float(stats.get("roas", 0.0))
            spend = float(stats.get("spend", 0.0))
            clicks = int(stats.get("clicks", 0))
            orders_clean = bool(stats.get("orders_clean", False))
            utm_campaign = stats.get("utm_campaign")

            campaign = {
                "spend": spend,
                "clicks": clicks,
                "orders_clean": orders_clean,
                "utm_campaign": utm_campaign,
            }

            decision: RiskDecision = self.risk_rules.decide(roas, current_budget, campaign)

            new_budget = decision.new_budget

            if decision.action == "scale":
                max_allowed_share_budget = self.max_daily_budget * self.max_campaign_share
                new_budget = min(new_budget, max_allowed_share_budget)

                daily_cap = current_budget * (1.0 + self.max_total_increase_per_day)
                new_budget = min(new_budget, daily_cap)

                if proposed_total + new_budget > self.max_daily_budget:
                    new_budget = max(
                        self.min_budget, self.max_daily_budget - proposed_total
                    )

            elif decision.action == "hold":
                new_budget = current_budget

            elif decision.action == "kill":
                new_budget = 0.0

            proposed_total += new_budget
            plans.append(
                BudgetPlan(
                    cid, decision.action, decision.reason, current_budget, new_budget
                )
            )

        return plans
