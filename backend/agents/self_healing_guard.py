from backend.agents.self_healing import self_healing_engine

class GuardedSelfHealing:
    def __init__(self, gap_threshold=0.5, confidence_threshold=0.5):
        self.gap_threshold = gap_threshold
        self.confidence_threshold = confidence_threshold

    def should_heal(self, reality_gap, confidence):
        if reality_gap is None:
            return False
        return reality_gap > self.gap_threshold and confidence < self.confidence_threshold

    def run(self, roas, diversity, structural_engine, reality_gap, confidence):
        if not self.should_heal(reality_gap, confidence):
            return []
        return self_healing_engine.heal(roas, diversity, structural_engine)


guarded_self_healing = GuardedSelfHealing()
