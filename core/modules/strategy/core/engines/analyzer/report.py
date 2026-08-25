"""归因 report：决定空间（不含 overall 胜率/净值）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .consts import SCHEMA_VERSION
from .attribution_pipeline import AttributionPipeline
from .insights import build_insights
from .report_narrative import build_hints_for_ui, build_scope_note
from .stages.base import AttributionContext


class AttributionReportBuilder:
    """从已收集的 source payload 生成 report.json。"""

    @classmethod
    def build(
        cls,
        source: Dict[str, Any],
        *,
        step: str,
        baseline_source: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        capture_keys = list(
            (source.get("inputs") or {}).get("capture", {}).get("keys") or []
        )
        coverage = dict(
            (source.get("inputs") or {}).get("capture", {}).get("coverage") or {}
        )
        decision_space = cls._decision_space(source)
        baseline_decision_space = (
            cls._decision_space(baseline_source) if baseline_source else None
        )
        attribution = AttributionPipeline.run(
            AttributionContext(
                source=source,
                step=step,
                decision_space=decision_space,
                baseline_source=baseline_source,
                baseline_decision_space=baseline_decision_space,
            )
        )
        classical = dict(attribution.get("classical") or {})
        classical["scope_note"] = build_scope_note(step)
        if step == "price":
            classical["skip_summary"] = _price_skip_summary(source)
        attribution = {**attribution, "classical": classical}
        hints_for_ui = build_hints_for_ui(
            step=step,
            decision_space=decision_space,
            attribution=attribution,
        )
        report = {
            "schema_version": SCHEMA_VERSION,
            "step": step,
            "version_id": str(source.get("version_id") or ""),
            "strategy_key": str(source.get("strategy_key") or ""),
            "generated_at": datetime.now().isoformat(),
            "manifest": {
                "capture_keys": capture_keys,
                "coverage": coverage,
                "outcome_fields": cls._outcome_fields(step),
            },
            "decision_space": decision_space,
            "attribution": attribution,
            "hints_for_ui": hints_for_ui,
        }
        # Persisted for CLI present + future BFF/UI; rebuild only if missing.
        report["insights"] = build_insights(report)
        return report

    @staticmethod
    def _outcome_fields(step: str) -> List[str]:
        from .step_config import get_step_outcome_config

        config = get_step_outcome_config(step)
        return [config.roi_field, config.result_field]

    @classmethod
    def _decision_space(cls, source: Dict[str, Any]) -> Dict[str, Any]:
        declared_core = dict(
            (source.get("inputs") or {}).get("declared", {}).get("core") or {}
        )
        capture_values = _gather_capture_values(source.get("entities") or [])
        capture_space = {
            key: cls._summarize_values(values)
            for key, values in sorted(capture_values.items())
        }
        declared_space = cls._summarize_declared_core(declared_core, capture_space)
        return {
            "capture": capture_space,
            "declared_core": declared_space,
        }

    @classmethod
    def _summarize_values(cls, values: Sequence[Any]) -> Dict[str, Any]:
        cleaned = [value for value in values if value not in (None, "")]
        if not cleaned:
            return {"role": "empty", "count": 0}

        numeric = [_as_float(value) for value in cleaned]
        if all(item is not None for item in numeric):
            nums = [float(item) for item in numeric if item is not None]
            unique = sorted(set(nums))
            if len(unique) == 1:
                return {
                    "role": "constant",
                    "dtype": "numeric",
                    "count": len(nums),
                    "value": unique[0],
                }
            return {
                "role": "varying",
                "dtype": "numeric",
                "count": len(nums),
                "unique_count": len(unique),
                "min": unique[0],
                "max": unique[-1],
            }

        texts = [str(value) for value in cleaned]
        unique_text = sorted(set(texts))
        if len(unique_text) == 1:
            return {
                "role": "constant",
                "dtype": "text",
                "count": len(texts),
                "value": unique_text[0],
            }
        return {
            "role": "varying",
            "dtype": "text",
            "count": len(texts),
            "unique_count": len(unique_text),
        }

    @classmethod
    def _summarize_declared_core(
        cls,
        declared_core: Dict[str, Any],
        capture_space: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for key, value in sorted(declared_core.items()):
            entry: Dict[str, Any] = {
                "role": "settings_knob",
                "value": value,
            }
            capture_summary = capture_space.get(key)
            if capture_summary is not None:
                entry["also_in_capture"] = True
                entry["capture_role"] = capture_summary.get("role")
            out[key] = entry
        return out


def _gather_capture_values(
    entities: Sequence[Dict[str, Any]],
) -> Dict[str, List[Any]]:
    out: Dict[str, List[Any]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        for investment in entity.get("investments") or []:
            if not isinstance(investment, dict):
                continue
            capture = investment.get("capture")
            if not isinstance(capture, dict):
                continue
            for key, value in capture.items():
                out.setdefault(str(key), []).append(value)
    return out


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _price_skip_summary(source: Dict[str, Any]) -> Dict[str, Any]:
    """Roll up ``engine.skip_reason`` for price-layer reports."""
    by_reason: Dict[str, int] = {}
    total = 0
    skipped = 0
    for entity in source.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for investment in entity.get("investments") or []:
            if not isinstance(investment, dict):
                continue
            total += 1
            engine = investment.get("engine")
            if not isinstance(engine, dict):
                continue
            reason = str(engine.get("skip_reason") or "").strip()
            if not reason:
                continue
            skipped += 1
            by_reason[reason] = int(by_reason.get(reason) or 0) + 1
    return {
        "investment_count": total,
        "skipped_count": skipped,
        "by_reason": dict(sorted(by_reason.items())),
    }


__all__ = ["AttributionReportBuilder"]
