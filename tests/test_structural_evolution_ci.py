import random

from backend.agents.structural_evolution import StructuralEvolution


def test_archive_grows_and_prunes():
    engine = StructuralEvolution()
    engine.max_archive_size = 10
    engine.initialize(n=2)

    for i in range(30):
        engine.score(engine.population[i % 2], performance=1.0 + (i * 0.01))

    assert len(engine.archive) == 10


def test_evolve_keeps_population_non_empty_and_non_identical():
    random.seed(7)
    engine = StructuralEvolution()
    engine.initialize(n=1)
    engine.score(engine.population[0], performance=1.0)
    engine.evolve()

    assert len(engine.population) > 0
    signatures = {engine._structure_signature(s) for s in engine.population}
    assert len(signatures) >= 2


def test_novelty_weight_adapts_on_low_diversity():
    random.seed(11)
    engine = StructuralEvolution()
    engine.initialize(n=1)
    engine.score(engine.population[0], performance=1.0)
    initial = engine.novelty_weight
    engine.evolve()

    assert engine.novelty_weight != initial
