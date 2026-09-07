"""Factor analysis pipeline — iterate stages, collect results."""

from .context import AnalysisStage, StageInput
from .pipeline import FactorAnalysisPipeline
from .stages import DEFAULT_STAGES

__all__ = [
    "AnalysisStage",
    "DEFAULT_STAGES",
    "FactorAnalysisPipeline",
    "StageInput",
]
