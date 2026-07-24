"""ReportManager.runtime 写门面（委托 shared simulation_input.RuntimeSnapshot）。

本文件:
- RuntimeReport: begin/load 走 shared RuntimeSnapshot
  边界: 仅绑 ReportManager；契约模型在 shared.services.simulation_input
"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.simulation_input.runtime_snapshot import (
    BacktestPeriod,
    RuntimeSnapshot,
    SavedRuntimeArtifacts,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

# 下游仍可能从本模块 import RuntimeSnapshot（enumerator 内部）；统一自 shared 再导出
__all__ = [
    "RuntimeReport",
    "RuntimeSnapshot",
    "BacktestPeriod",
    "SavedRuntimeArtifacts",
]


class RuntimeReport:
    """ReportManager.runtime 门面：启动快照读写。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    @staticmethod
    def resolve_period(effective_settings: Any) -> BacktestPeriod:
        return RuntimeSnapshot.resolve_period(effective_settings)

    def save_begin(
        self,
        *,
        entity_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        execution_mode: str,
        market_profile: str,
    ) -> SavedRuntimeArtifacts:
        snapshot = RuntimeSnapshot.build(
            strategy_key=self._manager.strategy_key,
            strategy_path=self._manager.strategy_path,
            version_id=self._manager.version_id,
            entity_ids=entity_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            execution_mode=execution_mode,
            market_profile=market_profile,
        )
        return snapshot.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return RuntimeSnapshot.load(self._manager.output_dir).to_dict()

    @property
    def entity_count(self) -> int:
        return RuntimeSnapshot.load(self._manager.output_dir).entity_count


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
        ReportManager,
    )
