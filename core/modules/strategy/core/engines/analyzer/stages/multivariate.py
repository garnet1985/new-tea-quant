"""Multivariate attribution stage — logistic win + OLS ROI."""
from __future__ import annotations

from typing import Any, Dict

from core.modules.analysis import Analysis

from ..dataset import (
    count_investments,
    extract_feature_matrix,
    list_varying_numeric_capture_keys,
)
from ..step_config import get_step_outcome_config
from .base import AttributionContext

_MIN_SAMPLES = 50
_MIN_FEATURES = 2


class MultivariateStage:
    name = "multivariate"

    def run(self, ctx: AttributionContext) -> Dict[str, Any]:
        keys = list_varying_numeric_capture_keys(ctx.decision_space)
        if len(keys) < _MIN_FEATURES:
            return {
                "status": "skipped",
                "reason": "insufficient_varying_fields",
                "required_features": _MIN_FEATURES,
                "found_features": len(keys),
            }

        n = count_investments(ctx.source)
        if n < _MIN_SAMPLES:
            return {
                "status": "skipped",
                "reason": "insufficient_samples",
                "required_samples": _MIN_SAMPLES,
                "n": n,
            }

        config = get_step_outcome_config(ctx.step)
        matrix, rois, wins = extract_feature_matrix(ctx.source, keys, config)
        if len(matrix) < _MIN_SAMPLES:
            return {
                "status": "skipped",
                "reason": "insufficient_aligned_samples",
                "n": len(matrix),
                "required_samples": _MIN_SAMPLES,
            }

        logistic = Analysis.Classical.logistic_win(
            matrix, keys, wins, min_samples=_MIN_SAMPLES
        )
        ols = Analysis.Classical.ols_weighted_roi(
            matrix, keys, rois, min_samples=_MIN_SAMPLES
        )
        stage_status = _stage_status(logistic, ols)

        return {
            "status": stage_status,
            "features": keys,
            "n": len(matrix),
            "logistic_win": logistic,
            "ols_weighted_roi": ols,
        }


def _stage_status(logistic: Dict[str, Any], ols: Dict[str, Any]) -> str:
    logistic_ok = logistic.get("status") == "ok"
    ols_ok = ols.get("status") == "ok"
    if logistic_ok and ols_ok:
        return "ok"
    if logistic_ok or ols_ok:
        return "partial"
    return "skipped"


__all__ = ["MultivariateStage"]
