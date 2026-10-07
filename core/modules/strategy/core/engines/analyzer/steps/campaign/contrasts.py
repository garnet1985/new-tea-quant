"""在有效设置上区分旋钮的有无和取值变化。写成 None 表示关掉，省略键表示继承快照。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.analysis import Analysis
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

_EQUAL_EPS = 1e-12


class KnobContrasts:
    """读取旋钮的有效值，并区分关掉和改取值。不按层过滤。"""

    @classmethod
    def declared_positions(cls, overlay: Mapping[str, Any]) -> Dict[str, Any]:
        """展开一格 overlay 动到的有效位置。goal 的直接子键整块替换。"""
        out: Dict[str, Any] = {}
        if not isinstance(overlay, Mapping):
            return out
        for section, body in overlay.items():
            if section == "goal" and isinstance(body, Mapping):
                for key, val in body.items():
                    out[f"goal.{key}"] = val
                continue
            cls._walk_leaves(body, str(section), out)
        return out

    @classmethod
    def declared_paths(cls, overlay: Mapping[str, Any]) -> List[str]:
        """返回一格覆盖动到的路径。"""
        return list(cls.declared_positions(overlay).keys())

    @classmethod
    def value_at(cls, raw: Any, path: str) -> Any:
        """读取点分路径上的值。"""
        cur = raw
        for part in str(path).split("."):
            if not isinstance(cur, Mapping) or part not in cur:
                return None
            cur = cur[part]
        return cur

    @classmethod
    def read(
        cls,
        source: Any,
        paths: Sequence[str],
    ) -> Dict[str, Any]:
        """一次读取多条路径的有效值。"""
        if isinstance(source, StrategySettings):
            raw: Any = source.raw_settings
        elif isinstance(source, Mapping):
            raw = source
        else:
            raw = {}
        return {path: cls.value_at(raw, path) for path in paths}

    @classmethod
    def union_paths(cls, overlays: Sequence[Mapping[str, Any]]) -> List[str]:
        """合并多格覆盖动到的路径，保持首次出现顺序。"""
        paths: List[str] = []
        seen = set()
        for overlay in overlays:
            if not isinstance(overlay, Mapping):
                continue
            for path in cls.declared_paths(overlay):
                if path in seen:
                    continue
                seen.add(path)
                paths.append(path)
        return paths

    @classmethod
    def is_off(cls, value: Any) -> bool:
        """该值是否表示关掉。"""
        return value is None

    @classmethod
    def scalar(cls, value: Any) -> Optional[float]:
        """把旋钮值收成可比较的数。"""
        if value is None:
            return None
        number = Analysis.Classical.coerce_float(value)
        if number is not None:
            return number
        if not isinstance(value, Mapping):
            return None
        stages = value.get("stages")
        if not isinstance(stages, list) or not stages:
            return None
        first = stages[0]
        if not isinstance(first, Mapping):
            return None
        return Analysis.Classical.coerce_float(first.get("ratio"))

    @classmethod
    def values_equal(cls, left: Any, right: Any) -> bool:
        """两个旋钮值是否相同。"""
        left_n = cls.scalar(left)
        right_n = cls.scalar(right)
        if left_n is not None and right_n is not None:
            return abs(left_n - right_n) < _EQUAL_EPS
        return left == right

    @classmethod
    def classify(cls, rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[str]]:
        """在有效值上分类：有/无 → 贡献度；取值变化 → 敏感度。可同属两章。"""
        paths = cls._union_knob_keys(rows)
        presence: List[str] = []
        sensitivity: List[str] = []
        for path in paths:
            values = [
                (row.get("knobs") or {}).get(path)
                if isinstance(row.get("knobs"), dict)
                else None
                for row in rows
            ]
            offs = [cls.is_off(value) for value in values]
            if any(offs) and not all(offs):
                presence.append(path)
            on_values = [value for value, off in zip(values, offs) if not off]
            if cls._distinct_count(on_values) >= 2:
                sensitivity.append(path)
        return {"presence": presence, "sensitivity": sensitivity}

    @classmethod
    def _walk_leaves(cls, obj: Any, prefix: str, out: Dict[str, Any]) -> None:
        if isinstance(obj, Mapping):
            if not obj:
                out[prefix] = obj
                return
            for key, val in obj.items():
                cls._walk_leaves(val, f"{prefix}.{key}", out)
            return
        out[prefix] = obj

    @classmethod
    def _union_knob_keys(cls, rows: Sequence[Mapping[str, Any]]) -> List[str]:
        keys: List[str] = []
        seen = set()
        for row in rows:
            knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
            for key in knobs:
                text = str(key)
                if text in seen:
                    continue
                seen.add(text)
                keys.append(text)
        return keys

    @classmethod
    def _distinct_count(cls, values: Sequence[Any]) -> int:
        unique: List[Any] = []
        for value in values:
            if any(cls.values_equal(value, seen) for seen in unique):
                continue
            unique.append(value)
        return len(unique)
