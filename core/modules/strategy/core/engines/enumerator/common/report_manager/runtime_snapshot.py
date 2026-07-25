"""ReportManager.runtime 写门面（委托 enumerator artifacts.RuntimeEnv）。

本文件:
- RuntimeReport: begin/load 走 artifacts.RuntimeEnv
  边界: 仅绑 ReportManager；内容模型在 enumerator.common.artifacts
"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
    BacktestPeriod,
    RuntimeEnv,
    SavedRuntimeEnvPaths,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

# 下游仍可能从本模块 import RuntimeEnv（enumerator 内部）；统一自 artifacts 再导出
__all__ = [
    "RuntimeReport",
    "RuntimeEnv",
    "BacktestPeriod",
    "SavedRuntimeEnvPaths",
]


class RuntimeReport:
    """ReportManager.runtime 门面：RuntimeEnv 读写。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

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
    ) -> SavedRuntimeEnvPaths:
        snapshot = RuntimeEnv.build(
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
        return RuntimeEnv.load(self._manager.output_dir).to_dict()

    @property
    def entity_count(self) -> int:
        return RuntimeEnv.load(self._manager.output_dir).entity_count


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )
