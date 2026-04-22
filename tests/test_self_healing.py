"""Tests for self-healing engine: stall detection, diversity collapse, mutation burst."""
import pytest
from backend.agents.self_healing import SelfHealingEngine, STALL_THRESHOLD, DIVERSITY_THRESHOLD
from backend.agents.structural_evolution import StructuralEvolution, random_structure


@pytest.fixture
def engine():
    e = StructuralEvolution()
    e.initialize(n=5)
    return e


@pytest.fixture
def healer():
    return SelfHealingEngine()


# ── stall detection ───────────────────────────────────────────────────────────

class TestStallDetection:
    def test_no_stall_on_first_call(self, healer):
        assert healer.detect_stall(1.0) is False

    def test_stall_detected_after_threshold(self, healer):
        healer.detect_stall(1.0)
        for _ in range(STALL_THRESHOLD):
            result = healer.detect_stall(0.9)
        assert result is True

    def test_stall_resets_on_improvement(self, healer):
        healer.detect_stall(1.0)
        for _ in range(STALL_THRESHOLD - 1):
            healer.detect_stall(0.9)
        healer.detect_stall(2.0)  # improvement resets counter
        assert healer.stall_counter == 0

    def test_stall_requires_consecutive_non_improvement(self, healer):
        healer.detect_stall(1.0)
        for i in range(STALL_THRESHOLD - 1):
            healer.detect_stall(0.5)
        # inject one improvement
        healer.detect_stall(3.0)
        # stall counter should have reset
        assert healer.stall_counter == 0


# ── diversity collapse detection ──────────────────────────────────────────────

class TestDiversityCollapse:
    def test_collapse_detected_below_threshold(self, healer):
        assert healer.detect_diversity_collapse(DIVERSITY_THRESHOLD - 0.01) is True

    def test_no_collapse_above_threshold(self, healer):
        assert healer.detect_diversity_collapse(DIVERSITY_THRESHOLD + 0.01) is False

    def test_exactly_at_threshold(self, healer):
        # at exactly the threshold, should NOT collapse (strictly less than)
        assert healer.detect_diversity_collapse(DIVERSITY_THRESHOLD) is False


# ── trigger_mutation_burst ────────────────────────────────────────────────────

class TestMutationBurst:
    def test_burst_increases_population(self, healer, engine):
        before = len(engine.population)
        healer.trigger_mutation_burst(engine)
        assert len(engine.population) > before

    def test_burst_triples_population(self, healer, engine):
        before = len(engine.population)
        healer.trigger_mutation_burst(engine)
        # each member spawns 2 mutants → 3× original
        assert len(engine.population) == before * 3

    def test_burst_mutants_differ_from_parents(self, healer, engine):
        originals = {s["id"] for s in engine.population}
        healer.trigger_mutation_burst(engine)
        new_ids = {s["id"] for s in engine.population} - originals
        assert len(new_ids) > 0

    def test_burst_preserves_originals(self, healer, engine):
        originals = {s["id"] for s in engine.population}
        healer.trigger_mutation_burst(engine)
        remaining = {s["id"] for s in engine.population}
        assert originals.issubset(remaining)


# ── reset_partial_population ──────────────────────────────────────────────────

class TestResetPartialPopulation:
    def test_reset_replaces_half(self, healer, engine):
        original_ids = {s["id"] for s in engine.population}
        healer.reset_partial_population(engine)
        new_ids = {s["id"] for s in engine.population}
        replaced = original_ids - new_ids
        assert len(replaced) >= len(original_ids) // 2

    def test_population_size_unchanged(self, healer, engine):
        before = len(engine.population)
        healer.reset_partial_population(engine)
        assert len(engine.population) == before


# ── exploration_spike ─────────────────────────────────────────────────────────

class TestExplorationSpike:
    def test_spike_increases_novelty_override(self, healer, engine):
        import backend.agents.structural_evolution as se
        baseline = getattr(engine, "_novelty_override", se.NOVELTY_WEIGHT)
        healer.exploration_spike(engine)
        assert engine._novelty_override > baseline

    def test_spike_caps_at_0_9(self, healer, engine):
        engine._novelty_override = 0.88
        healer.exploration_spike(engine)
        assert engine._novelty_override <= 0.9


# ── heal (integration) ────────────────────────────────────────────────────────

class TestHeal:
    def test_heal_returns_actions_list(self, healer, engine):
        result = healer.heal(roas=1.0, diversity=0.5, structural_engine=engine)
        assert isinstance(result, list)

    def test_heal_triggers_mutation_on_stall(self, healer, engine):
        healer.prev_roas = 2.0
        healer.stall_counter = STALL_THRESHOLD - 1
        actions = healer.heal(roas=1.5, diversity=0.5, structural_engine=engine)
        assert "mutation_burst" in actions

    def test_heal_triggers_diversity_reset_on_collapse(self, healer, engine):
        actions = healer.heal(roas=1.5, diversity=0.0, structural_engine=engine)
        assert "diversity_reset" in actions

    def test_heal_no_action_when_healthy(self, healer, engine):
        healer.prev_roas = 1.0
        actions = healer.heal(roas=1.5, diversity=0.5, structural_engine=engine)
        assert actions == []
