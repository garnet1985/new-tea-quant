"""因子矩阵：各轴取值的笛卡尔积，展开成 overlay 行。

``attribution.overlays`` 是逐项对照；``attribution.matrix`` 是多轴网格。二者可同时写。
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.execute_fp_whitelist import (
    EXECUTE_SETTINGS_FIELDS,
    NON_EXECUTE_SETTINGS_FIELDS,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .overlay import SettingsOverlay

_MAX_CELLS = 128
_MIN_AXES = 2
_MIN_LEVELS = 2


class SettingsMatrix:
    """各轴 list → 笛卡尔积 overlay。goal 的直接孩子整块是一轴。"""

    @classmethod
    def expand(cls, raw: Mapping[str, Any]) -> Tuple[Dict[str, Any], ...]:
        axes = cls.axes(raw)
        if not axes:
            return ()
        keys = [path for path, _ in axes]
        pools = [levels for _, levels in axes]
        rows: List[Dict[str, Any]] = []
        for combo in itertools.product(*pools):
            tree: Dict[str, Any] = {}
            for path, value in zip(keys, combo):
                cls._assign(tree, path, value)
            rows.append(tree)
        return tuple(rows)

    @classmethod
    def axes(cls, raw: Mapping[str, Any]) -> List[Tuple[str, Tuple[Any, ...]]]:
        out: List[Tuple[str, Tuple[Any, ...]]] = []
        if not isinstance(raw, Mapping):
            return out
        for section, body in raw.items():
            if section == "goal" and isinstance(body, Mapping):
                for key, val in body.items():
                    if isinstance(val, list):
                        out.append((f"goal.{key}", tuple(val)))
                continue
            cls._walk(body, str(section), out)
        return out

    @classmethod
    def validate(cls, raw: Any, report: ValidationReport) -> None:
        if raw is None:
            return
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, Mapping)):
            SettingsBase.add_critical(
                report,
                "matrix",
                "attribution.matrix 须为各轴取值的 dict；逐项对照请写 overlays",
                suggested_fix='matrix = {"core": {"rsi_oversold_threshold": [20, 25]}}',
            )
            return
        if not isinstance(raw, Mapping):
            SettingsBase.add_critical(
                report,
                "matrix",
                "attribution.matrix 须为 dict",
                suggested_fix='matrix = {"core": {"rsi_oversold_threshold": [20, 25]}}',
            )
            return
        if not raw:
            return
        for key in raw:
            if key in NON_EXECUTE_SETTINGS_FIELDS or key not in EXECUTE_SETTINGS_FIELDS:
                SettingsBase.add_critical(
                    report,
                    f"matrix.{key}",
                    f"matrix 只允许 execute_fp 白名单块，不能写 {key!r}",
                    suggested_fix=f"允许 {sorted(EXECUTE_SETTINGS_FIELDS)}",
                )
        axes = cls.axes(raw)
        for path, levels in axes:
            if len(levels) < _MIN_LEVELS:
                SettingsBase.add_critical(
                    report,
                    f"matrix.{path}",
                    f"每一轴至少 {_MIN_LEVELS} 个取值",
                    suggested_fix="单档钉在 settings 里；矩阵轴要能对照",
                )
                continue
            overlay_probe = {}
            cls._assign(overlay_probe, path, levels[0] if levels else None)
            overlay_report = SettingsOverlay.from_dict(overlay_probe).validate()
            for err in overlay_report.errors:
                err = dict(err)
                err["field_path"] = (
                    f"matrix.{path}.{err.get('field_path') or ''}"
                ).rstrip(".")
                report.errors.append(err)
                report.is_valid = False
        if len(axes) < _MIN_AXES:
            SettingsBase.add_critical(
                report,
                "matrix",
                f"matrix 至少 {_MIN_AXES} 轴（多因子交叉）；单轴扫取值请写 overlays",
            )
            return
        n = 1
        for _path, levels in axes:
            n *= max(len(levels), 1)
        if n > _MAX_CELLS:
            SettingsBase.add_critical(
                report,
                "matrix",
                f"笛卡尔积 {n} 格超过上限 {_MAX_CELLS}",
                suggested_fix="减少轴或每轴档数；全因子太大就拆成 overlays 加一对交叉",
            )

    @classmethod
    def _walk(
        cls,
        obj: Any,
        prefix: str,
        out: List[Tuple[str, Tuple[Any, ...]]],
    ) -> None:
        if isinstance(obj, list):
            out.append((prefix, tuple(obj)))
            return
        if isinstance(obj, Mapping):
            if not obj:
                return
            for key, val in obj.items():
                cls._walk(val, f"{prefix}.{key}", out)

    @classmethod
    def _assign(cls, tree: Dict[str, Any], path: str, value: Any) -> None:
        parts = [part for part in str(path).split(".") if part]
        if not parts:
            return
        cur: Dict[str, Any] = tree
        for part in parts[:-1]:
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[parts[-1]] = value
