"""Tests for structural evolution: population, mutation, selection, diversity."""
import pytest
from backend.agents.structural_evolution import (
    StructuralEvolution,
    random_structure,
    mutate_structure,
    structure_distance,
    novelty_score,
    DIVERSITY_THRESHOLD,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    e = StructuralEvolution()
    e.initialize(n=5)
    return e


# ── initialization ────────────────────────────────────────────────────────────

class TestInitialization:
    def test_population_size(self, engine):
        assert len(engine.population) == 5

    def test_structures_have_required_keys(self, engine):
        for s in engine.population:
            assert "id" in s
            assert "weights" in s
            assert "features" in s
            assert "planning_depth" in s

    def test_ids_unique(self, engine):
        ids = [s["id"] for s in engine.population]
        assert len(ids) == len(set(ids))

    def test_weights_in_range(self, engine):
        for s in engine.population:
            for k, v in s["weights"].items():
                assert 0.0 <= v <= 1.0, f"Weight {k}={v} out of [0,1]"

    def test_planning_depth_in_range(self, engine):
        for s in engine.population:
            assert 1 <= s["planning_depth"] <= 5


# ── random_structure ──────────────────────────────────────────────────────────

def test_random_structure_has_unique_id():
    a = random_structure()
    b = random_structure()
    assert a["id"] != b["id"]


def test_random_structure_memory_initialized():
    s = random_structure()
    assert s["memory"]["avg_perf"] == 0.0
    assert s["memory"]["count"] == 0


# ── structure_distance ────────────────────────────────────────────────────────

class TestStructureDistance:
    def test_distance_to_self_is_zero(self):
        s = random_structure()
        assert structure_distance(s, s) == 0.0

    def test_distance_symmetric(self):
        a = random_structure()
        b = random_structure()
        assert abs(structure_distance(a, b) - structure_distance(b, a)) < 1e-9

    def test_distance_in_range(self):
        for _ in range(20):
            a = random_structure()
            b = random_structure()
            d = structure_distance(a, b)
            assert 0.0 <= d <= 1.0


# ── mutate_structure ──────────────────────────────────────────────────────────

class TestMutation:
    def test_mutant_has_new_id(self):
        s = random_structure()
        m = mutate_structure(s)
        assert m["id"] != s["id"]

    def test_mutant_preserves_parent_id(self):
        s = random_structure()
        m = mutate_structure(s)
        assert m["parent_id"] == s["id"]

    def test_mutant_weights_in_range(self):
        s = random_structure()
        for _ in range(10):
            m = mutate_structure(s, intensity=0.5)
            for v in m["weights"].values():
                assert v >= 0.0

    def test_high_intensity_produces_more_change(self):
        s = random_structure()
        dists_lo = [structure_distance(s, mutate_structure(s, intensity=0.01)) for _ in range(30)]
        dists_hi = [structure_distance(s, mutate_structure(s, intensity=0.9)) for _ in range(30)]
        assert sum(dists_hi) >= sum(dists_lo)


# ── scoring & selection ───────────────────────────────────────────────────────

class TestScoring:
    def test_score_recorded(self, engine):
        s = engine.population[0]
        engine.score(s, 1.5)
        assert engine.avg_score(s["id"]) == pytest.approx(1.5)

    def test_avg_score_multiple(self, engine):
        s = engine.population[0]
        engine.score(s, 1.0)
        engine.score(s, 3.0)
        assert engine.avg_score(s["id"]) == pytest.approx(2.0)

    def test_select_best_returns_top_k(self, engine):
        for i, s in enumerate(engine.population):
            engine.score(s, float(i))
        best = engine.select_best(top_k=3)
        assert len(best) == 3

    def test_lineage_score_tracked(self, engine):
        parent = engine.population[0]
        child = mutate_structure(parent)
        engine.score(child, 2.0)
        assert engine.lineage_score(parent["id"]) == pytest.approx(2.0)


# ── diversity ─────────────────────────────────────────────────────────────────

class TestDiversity:
    def test_population_diversity_returns_float(self, engine):
        d = engine.population_diversity()
        assert isinstance(d, float)

    def test_population_diversity_in_range(self, engine):
        d = engine.population_diversity()
        assert 0.0 <= d <= 1.0

    def test_identical_population_low_diversity(self):
        e = StructuralEvolution()
        s = random_structure()
        e.population = [s] * 3  # same object = zero distance
        assert e.population_diversity() == pytest.approx(0.0)

    def test_single_member_diversity_is_one(self):
        e = StructuralEvolution()
        e.population = [random_structure()]
        assert e.population_diversity() == 1.0

    def test_enforce_diversity_removes_duplicates(self, engine):
        s = random_structure()
        pop = [s] * 5  # all identical → only 1 survives
        diverse = engine.enforce_diversity(pop)
        assert len(diverse) == 1


# ── evolve ────────────────────────────────────────────────────────────────────

class TestEvolve:
    def test_evolve_records_diversity(self, engine):
        for s in engine.population:
            engine.score(s, 1.5)
        engine.evolve()
        assert len(engine.diversity_history) == 1
        assert 0.0 <= engine.diversity_history[0] <= 1.0

    def test_evolve_maintains_population(self, engine):
        for s in engine.population:
            engine.score(s, 1.2)
        engine.evolve()
        assert len(engine.population) >= 1

    def test_evolve_population_cap(self, engine):
        for s in engine.population:
            engine.score(s, 2.0)
        engine.evolve()
        assert len(engine.population) <= 10

    def test_multiple_evolve_cycles_accumulate_history(self, engine):
        for _ in range(3):
            for s in engine.population:
                engine.score(s, 1.0)
            engine.evolve()
        assert len(engine.diversity_history) == 3
