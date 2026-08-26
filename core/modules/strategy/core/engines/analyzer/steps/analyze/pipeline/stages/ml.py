"""ML factor analysis — XGBoost feature importance."""
from __future__ import annotations

from typing import Any, Dict

from core.modules.analysis import Analysis

from ...data import CaptureDataset, StepOutcomeRegistry
from ..context import StageInput

_MIN_SAMPLES = 500
_MIN_FEATURES = 2


class MLStage:
    name = "ml"

    def run(self, stage_input: StageInput) -> Dict[str, Any]:
        keys = CaptureDataset.list_varying_numeric_capture_keys(
            stage_input.decision_space
        )
        if len(keys) < _MIN_FEATURES:
            return {
                "status": "skipped",
                "reason": "insufficient_varying_fields",
            }

        config = StepOutcomeRegistry.get(stage_input.step)
        matrix, rois, _ = CaptureDataset.extract_feature_matrix(
            stage_input.source, keys, config
        )
        if len(matrix) < _MIN_SAMPLES:
            return {
                "status": "skipped",
                "reason": "insufficient_samples",
                "required_samples": _MIN_SAMPLES,
                "n": len(matrix),
            }

        xgb_result = Analysis.ML.xgb_feature_importance(matrix, keys, rois)
        return {
            "status": xgb_result.get("status", "skipped"),
            "features": keys,
            "n": len(matrix),
            "xgb": xgb_result,
        }


__all__ = ["MLStage"]
