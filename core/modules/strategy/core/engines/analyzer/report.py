"""归因 report：决定空间（不含 overall 胜率/净值）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .consts import SCHEMA_VERSION


class AttributionReportBuilder:
    """从已收集的 source payload 生成 report.json。"""

    @classmethod
    def build(cls, source: Dict[str, Any], *, step: str) -> Dict[str, Any]:
        capture_keys = list(
            (source.get("inputs") or {}).get("capture", {}).get("keys") or []
        )
        coverage = dict(
            (source.get("inputs") or {}).get("capture", {}).get("coverage") or {}
        )
        decision_space = cls._decision_space(source)
        return {
            "schema_version": SCHEMA_VERSION,
            "step": step,
            "version_id": str(source.get("version_id") or ""),
            "strategy_key": str(source.get("strategy_key") or ""),
            "generated_at": datetime.now().isoformat(),
            "manifest": {
                "capture_keys": capture_keys,
                "coverage": coverage,
            },
            "decision_space": decision_space,
        }

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


__all__ = ["AttributionReportBuilder"]
