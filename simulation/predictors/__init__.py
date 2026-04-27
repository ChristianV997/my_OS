"""simulation.predictors — per-domain interpretable predictors.

Each predictor is a thin, rule-based or lightweight-ML module that scores
one specific dimension BEFORE the full Ridge model fires.

Predictors are used as feature sources by simulation/features.py and as
stand-alone scores when the main model is not yet trained.

Available
---------
hooks   — hook-level engagement predictor (pattern history)
niche   — niche / product-level virality estimate
"""
from simulation.predictors.hooks import HookPredictor, hook_predictor
from simulation.predictors.niche import NichePredictor, niche_predictor

__all__ = [
    "HookPredictor", "hook_predictor",
    "NichePredictor", "niche_predictor",
]
