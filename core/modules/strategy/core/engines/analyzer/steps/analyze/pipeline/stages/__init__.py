"""Factor analysis stages — add a new member here to extend the pipeline."""
from __future__ import annotations

from .ml import MLStage
from .multivariate import MultivariateStage
from .run_comparison import RunComparisonStage
from .univariate import UnivariateStage

DEFAULT_STAGES = [
    UnivariateStage(),
    MultivariateStage(),
    RunComparisonStage(),
    MLStage(),
]

__all__ = [
    "DEFAULT_STAGES",
    "MLStage",
    "MultivariateStage",
    "RunComparisonStage",
    "UnivariateStage",
]
