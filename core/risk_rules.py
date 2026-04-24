from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RiskDecision:
    action: str  # "hold" | "scale" | "kill"
    reason: str
    new_budget: float = 0.0


class RiskRules:
    """Threshold-based ROAS → budget action rules."""

    def __init__(
        self,
        min_spend_for_decision: float = 20.0,
        min_clicks_for_decision: int = 50,
        kill_roas: float = 0.8,
        hold_roas: float = 1.2,
        scale_roas: float = 1.8,
        aggressive_roas: float = 2.5,
        max_campaign_share: float = 0.35,
        max_daily_increase: float = 0.30,
        max_drawdown: float = 0.30,
    ):
        self.min_spend_for_decision = min_spend_for_decision
        self.min_clicks_for_decision = min_clicks_for_decision
        self.kill_roas = kill_roas
        self.hold_roas = hold_roas
        self.scale_roas = scale_roas
        self.aggressive_roas = aggressive_roas
        self.max_campaign_share = max_campaign_share
        self.max_daily_increase = max_daily_increase
        self.max_drawdown = max_drawdown

    def validate_data(self, campaign: Dict) -> bool:
        return bool(
            campaign.get("utm_campaign")
            and campaign.get("orders_clean", False)
            and campaign.get("spend", 0) >= self.min_spend_for_decision
            and campaign.get("clicks", 0) >= self.min_clicks_for_decision
        )

    def should_stop_for_drawdown(
        self, current_equity: float, peak_equity: float
    ) -> bool:
        if peak_equity <= 0:
            return False
        drawdown = (peak_equity - current_equity) / peak_equity
        return drawdown > self.max_drawdown

    def decide(
        self, roas: float, current_budget: float, campaign: Dict
    ) -> RiskDecision:
        if not self.validate_data(campaign):
            return RiskDecision("hold", "insufficient_or_dirty_data", current_budget)

        if roas < self.kill_roas:
            return RiskDecision("kill", f"roas_below_{self.kill_roas}", 0.0)

        if roas < self.hold_roas:
            return RiskDecision("hold", "learning_band", current_budget)

        if roas < self.scale_roas:
            return RiskDecision("scale", "modest_winner", current_budget * 1.15)

        if roas < self.aggressive_roas:
            return RiskDecision("scale", "strong_winner", current_budget * 1.35)

        return RiskDecision("scale", "elite_winner", current_budget * 1.60)
