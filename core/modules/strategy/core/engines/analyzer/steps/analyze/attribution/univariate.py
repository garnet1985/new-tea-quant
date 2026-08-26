"""Univariate attribution stage → ``modules.analysis`` stubs."""
from __future__ import annotations

from typing import Any, Dict

from core.modules.analysis import Analysis

from ..capture_dataset import CaptureDataset
from ....support.step_outcome import StepOutcomeRegistry
from ..context import AttributionContext


class UnivariateStage:
    name = "univariate"

    def run(self, ctx: AttributionContext) -> Dict[str, Any]:
        config = StepOutcomeRegistry.get(ctx.step)
        keys = CaptureDataset.list_varying_numeric_capture_keys(ctx.decision_space)
        if not keys:
            return {
                "status": "skipped",
                "reason": "no_varying_numeric_capture",
                "fields": {},
            }

        fields: Dict[str, Any] = {}
        for key in keys:
            values, rois, wins = CaptureDataset.extract_capture_series(
                ctx.source, key, config
            )
            if len(values) < 2:
                fields[key] = {
                    "status": "skipped",
                    "reason": "insufficient_samples",
                    "n": len(values),
                }
                continue
            fields[key] = {
                "method": "quantile_buckets",
                "n": len(values),
                "buckets": Analysis.Classical.quantile_buckets(
                    values, rois, wins
                ),
                "correlation": Analysis.Classical.spearman_correlation(
                    values, rois
                ),
            }

        stage_status = "ok"
        for field in fields.values():
            if not isinstance(field, dict):
                continue
            if field.get("status") == "skipped":
                stage_status = "partial"
                continue
            buckets = field.get("buckets")
            corr = field.get("correlation")
            if isinstance(buckets, dict) and buckets.get("status") != "ok":
                stage_status = "partial"
            if isinstance(corr, dict) and corr.get("status") not in ("ok", "skipped"):
                stage_status = "partial"

        return {
            "status": stage_status,
            "fields": fields,
        }


__all__ = ["UnivariateStage"]
