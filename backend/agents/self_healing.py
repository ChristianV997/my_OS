import random

STALL_THRESHOLD = 5
DIVERSITY_THRESHOLD = 0.1


class SelfHealingEngine:
    def __init__(self):
        self.stall_counter = 0
        self.prev_roas = None

    def detect_stall(self, roas):
        if self.prev_roas is None:
            self.prev_roas = roas
            return False

        if roas <= self.prev_roas:
            self.stall_counter += 1
        else:
            self.stall_counter = 0

        self.prev_roas = roas

        return self.stall_counter >= STALL_THRESHOLD

    def detect_diversity_collapse(self, diversity):
        return diversity < DIVERSITY_THRESHOLD

    def trigger_mutation_burst(self, structural_engine):
        from backend.agents.structural_evolution import mutate_structure
        new_population = []
        for s in structural_engine.population:
            new_population.append(s)
            for _ in range(2):
                new_population.append(mutate_structure(s, structural_engine.global_knowledge, intensity=0.3))
        structural_engine.population = new_population

    def reset_partial_population(self, structural_engine):
        from backend.agents.structural_evolution import random_structure
        half = len(structural_engine.population) // 2
        for i in range(half):
            structural_engine.population[i] = random_structure()

    def exploration_spike(self, structural_engine):
        # NOVELTY_WEIGHT is a module constant; track override on the engine instance
        import backend.agents.structural_evolution as se
        current = getattr(structural_engine, "_novelty_override", se.NOVELTY_WEIGHT)
        structural_engine._novelty_override = min(0.9, current + 0.2)

    def heal(self, roas, diversity, structural_engine):
        actions = []

        if self.detect_stall(roas):
            self.trigger_mutation_burst(structural_engine)
            self.exploration_spike(structural_engine)
            actions.append("mutation_burst")

        if self.detect_diversity_collapse(diversity):
            self.reset_partial_population(structural_engine)
            self.exploration_spike(structural_engine)
            actions.append("diversity_reset")

        return actions


self_healing_engine = SelfHealingEngine()
