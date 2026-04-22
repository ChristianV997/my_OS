import random
from backend.agents.structural_evolution import mutate_structure

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
        new_population = []
        for s in structural_engine.population:
            for _ in range(2):
                mutated = mutate_structure(s, structural_engine.global_knowledge, intensity=0.3)
                new_population.append(mutated)
        diverse_population = structural_engine.enforce_diversity(new_population)
        if diverse_population:
            structural_engine.population = diverse_population
        elif new_population:
            structural_engine.population = new_population
        else:
            structural_engine.initialize()

    def reset_partial_population(self, structural_engine):
        half = len(structural_engine.population) // 2
        if half == 0:
            return
        for i in range(half):
            base = random.choice(structural_engine.population)
            structural_engine.population[i] = mutate_structure(
                base,
                structural_engine.global_knowledge,
                intensity=0.4,
            )

    def exploration_spike(self, structural_engine):
        structural_engine.novelty_weight = min(0.9, structural_engine.novelty_weight + 0.2)

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
