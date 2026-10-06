"""把 attribution.rolling 的窗口展开成格子：每一段区间一份 overlay。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from ..campaign.config import SettingsOverlay
from ..campaign.plan import AttributionCell
from .config import RollingSettings


class WindowExpander:
    """快照 ⊕ 窗口起止日 → StrategySettings。"""

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: RollingSettings,
    ) -> List[AttributionCell]:
        disk = load_settings_dict_from_folder(folder)
        snapshot = StrategySettings.to_usable(dict(disk))
        return cls.expand(snapshot, config)

    @classmethod
    def expand(
        cls,
        snapshot: StrategySettings,
        config: RollingSettings,
    ) -> List[AttributionCell]:
        return [
            cls._from_window(i, snapshot, window)
            for i, window in enumerate(config.windows)
        ]

    @classmethod
    def _from_window(
        cls,
        index: int,
        snapshot: StrategySettings,
        window: Dict[str, str],
    ) -> AttributionCell:
        execution = {}
        simulation = snapshot.raw_settings.get("simulation")
        if isinstance(simulation, dict) and isinstance(simulation.get("execution"), dict):
            execution = dict(simulation.get("execution") or {})
        execution["start_date"] = window["start"]
        execution["end_date"] = window["end"]
        overlay: Dict[str, Any] = {"simulation": {"execution": execution}}
        row = SettingsOverlay.from_dict(overlay)
        effective = row.merge_onto(snapshot)
        return AttributionCell(
            index=index,
            overlay=overlay,
            runtime_settings=dict(overlay),
            execute_settings=StrategySettings.extract_execute_settings(effective),
            effective=effective,
            version_id=None,
        )
