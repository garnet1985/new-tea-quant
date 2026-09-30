"""把 attribution.py 展开成格子：matrix 一行一格，或 versions 选号。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from .config import AttributionSettings
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

    @property
    def is_select(self) -> bool:
        return self.version_id is not None


@dataclass(frozen=True)
class AttributionTask:
    """一格对应的可执行任务（查缓存 / 补跑）。"""

    cell: AttributionCell
    kind: SimulateKind
    fill_missing: bool

    @classmethod
    def from_cells(
        cls,
        cells: Sequence[AttributionCell],
        config: Any,
    ) -> List["AttributionTask"]:
        kind = config.simulate_kind
        return [
            cls(cell=cell, kind=kind, fill_missing=config.fill_missing)
            for cell in cells
        ]


class CellExpander:
    """快照 ⊕ overlay → StrategySettings；选号则只带 version_id。"""

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: AttributionSettings,
    ) -> List[AttributionCell]:
        disk = load_settings_dict_from_folder(folder)
        snapshot = StrategySettings.to_usable(dict(disk))
        return cls.expand(snapshot, config)

    @classmethod
    def expand(
        cls,
        snapshot: StrategySettings,
        config: AttributionSettings,
    ) -> List[AttributionCell]:
        if config.is_select:
            return [
                AttributionCell(
                    index=i,
                    overlay={},
                    runtime_settings={},
                    execute_settings={},
                    effective=None,
                    version_id=vid,
                )
                for i, vid in enumerate(config.versions)
            ]
        return [
            cls._from_overlay(i, snapshot, row)
            for i, row in enumerate(config.matrix)
        ]

    @classmethod
    def _from_overlay(
        cls,
        index: int,
        snapshot: StrategySettings,
        row: SettingsOverlay,
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
        )
