"""把 attribution.py 展开成格子：overlays 逐项、matrix 笛卡尔积，或 versions 选号。

overlays 与 matrix 各自成表；执行并集按 ``execute_settings`` 去重。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from .config import AttributionSettings
from .grid import SettingsMatrix
from .overlay import SettingsOverlay


@dataclass(frozen=True)
class AttributionCell:
    """战役一格：目标身份，还不是一次 Run。"""

    index: int
    overlay: Dict[str, Any]
    runtime_settings: Dict[str, Any]
    execute_settings: Dict[str, Any]
    effective: Optional[StrategySettings] = None
    version_id: Optional[int] = None
    family: str = ""

    @property
    def is_select(self) -> bool:
        return self.version_id is not None


@dataclass(frozen=True)
class ParameterPlan:
    """overlays / matrix / 选号各一套格子。"""

    overlays: Tuple[AttributionCell, ...] = ()
    matrix: Tuple[AttributionCell, ...] = ()
    selected: Tuple[AttributionCell, ...] = ()

    def families(self) -> List[Tuple[str, List[AttributionCell]]]:
        out: List[Tuple[str, List[AttributionCell]]] = []
        if self.selected:
            out.append(("select", list(self.selected)))
        if self.overlays:
            out.append(("overlays", list(self.overlays)))
        if self.matrix:
            out.append(("matrix", list(self.matrix)))
        return out

    def execute_source_cells(self) -> List[AttributionCell]:
        if self.selected:
            return list(self.selected)
        return list(self.overlays) + list(self.matrix)

    def listed_cells(self) -> List[AttributionCell]:
        """单家族保持原 index；两家族拼在一起时重编，避免撞号。"""
        parts = [
            list(group)
            for group in (self.selected, self.overlays, self.matrix)
            if group
        ]
        if len(parts) <= 1:
            return list(parts[0] if parts else [])
        out: List[AttributionCell] = []
        for i, cell in enumerate(self.execute_source_cells()):
            out.append(replace(cell, index=i))
        return out


def cell_identity(cell: AttributionCell) -> str:
    """回测身份：选号用 version；其余用 execute_settings。"""
    if cell.is_select:
        return f"select:{cell.version_id}"
    return json.dumps(
        cell.execute_settings,
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )


@dataclass(frozen=True)
class AttributionTask:
    """一格对应的可执行任务（交给 ``Strategy.simulate`` 或按号读取）。"""

    cell: AttributionCell
    kind: SimulateKind
    steps: Tuple[SimulateKind, ...] = ()

    @classmethod
    def from_cells(
        cls,
        cells: Sequence[AttributionCell],
        config: Any,
    ) -> List["AttributionTask"]:
        steps = tuple(config.steps)
        kind = config.simulate_kind
        return [cls(cell=cell, kind=kind, steps=steps) for cell in cells]


class CellExpander:
    """快照 ⊕ overlay → StrategySettings；选号则只带 version_id。"""

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: AttributionSettings,
    ) -> List[AttributionCell]:
        return cls.plan_from_folder(folder, config).listed_cells()

    @classmethod
    def plan_from_folder(
        cls,
        folder: Path,
        config: AttributionSettings,
    ) -> ParameterPlan:
        disk = load_settings_dict_from_folder(folder)
        snapshot = StrategySettings.to_usable(dict(disk))
        return cls.plan(snapshot, config)

    @classmethod
    def expand(
        cls,
        snapshot: StrategySettings,
        config: AttributionSettings,
    ) -> List[AttributionCell]:
        return cls.plan(snapshot, config).listed_cells()

    @classmethod
    def plan(
        cls,
        snapshot: StrategySettings,
        config: AttributionSettings,
    ) -> ParameterPlan:
        if config.is_select:
            selected = tuple(
                AttributionCell(
                    index=i,
                    overlay={},
                    runtime_settings={},
                    execute_settings={},
                    effective=None,
                    version_id=vid,
                    family="select",
                )
                for i, vid in enumerate(config.versions)
            )
            return ParameterPlan(selected=selected)
        overlays = tuple(
            cls._from_overlay(i, snapshot, row, family="overlays")
            for i, row in enumerate(config.overlays)
        )
        matrix: Tuple[AttributionCell, ...] = ()
        if config.has_matrix:
            raw = config.raw_settings.get("matrix")
            rows = SettingsMatrix.expand(raw if isinstance(raw, dict) else {})
            matrix = tuple(
                cls._from_overlay(i, snapshot, SettingsOverlay.from_dict(row), family="matrix")
                for i, row in enumerate(rows)
            )
        return ParameterPlan(overlays=overlays, matrix=matrix)

    @classmethod
    def _from_overlay(
        cls,
        index: int,
        snapshot: StrategySettings,
        row: SettingsOverlay,
        *,
        family: str = "",
    ) -> AttributionCell:
        overlay = row.to_dict()
        effective = row.merge_onto(snapshot)
        return AttributionCell(
            index=index,
            overlay=overlay,
            runtime_settings=dict(overlay),
            execute_settings=StrategySettings.extract_execute_settings(effective),
            effective=effective,
            version_id=None,
            family=family,
        )
