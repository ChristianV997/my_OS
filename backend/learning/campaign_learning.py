from collections import defaultdict

class CampaignLearning:

    def __init__(self):
        self.history = defaultdict(list)

    def update(self, action, outcome):
        campaign_id = outcome.get("campaign_id")
        roas = outcome.get("roas", 0)

        if campaign_id:
            self.history[campaign_id].append(roas)

            if len(self.history[campaign_id]) > 100:
                self.history[campaign_id] = self.history[campaign_id][-100:]

    def score(self, campaign_id):
        vals = self.history.get(campaign_id, [])
        if not vals:
            return 0
        return sum(vals) / len(vals)

    def best_campaigns(self):
        scores = {c: self.score(c) for c in self.history}
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


campaign_learning = CampaignLearning()
