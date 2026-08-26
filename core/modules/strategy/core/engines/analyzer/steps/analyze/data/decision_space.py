"""Step 2 — 决定空间（strategy 语义：settings_knob + capture 角色）。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from core.modules.analysis import Analysis


class DecisionSpaceBuilder:
    @classmethod
    def build(cls, source: Dict[str, Any]) -> Dict[str, Any]:
        declared_core = dict(
            (source.get("inputs") or {}).get("declared", {}).get("core") or {}
        )
        capture_values = cls._gather_capture_values(source.get("entities") or [])
        capture_space = {
            key: Analysis.Classical.summarize_column(values)
            for key, values in sorted(capture_values.items())
        }
        declared_space = cls._summarize_declared_core(declared_core, capture_space)
        return {
            "capture": capture_space,
            "declared_core": declared_space,
        }

    @classmethod
    def _gather_capture_values(
        cls,
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
