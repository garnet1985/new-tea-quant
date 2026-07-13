"""entity_based 枚举产物：version 目录 + job 级 CSV 写入。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
    ReportManager,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    GoalAchievements,
    StockInvestments,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

logger = logging.getLogger(__name__)

LEGACY_SCOPE_STOCK_IDS_FILENAME = "0_scope_stock_ids.txt"
LEGACY_RUN_PRECONDITION_FILENAME = "0_run_precondition.json"


@dataclass
class EntityBasedEnumeratorRecorder(SimulationOutputRecorder):
    """entity_based 枚举输出：run 产物 + 子进程 CSV。"""

    settings_fp: str = ""
    env_fp: str = ""
    _job_buffer: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    @classmethod
    def init(
        cls,
        strategy_id: str,
        *,
        entity_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        execution_mode: str,
        market_profile: str,
    ) -> EntityBasedEnumeratorRecorder:
        root = ProjectContext.path.get_strategy_directory_simulation_enum(strategy_id)
        manager = ReportManager.begin(
            strategy_id,
            entity_ids=entity_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            execution_mode=execution_mode,
            market_profile=market_profile,
        )
        return cls(
            output_dir=manager.output_dir,
            strategy_id=strategy_id,
            version_id=manager.version_id,
            version_dir_name=str(manager.version_id),
            settings_fp=settings_fp,
            env_fp=env_fp,
        )

    def buffer_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        self._job_buffer.extend(list(opportunities or []))

    def flush_job_opportunities(self) -> Dict[str, int]:
        """将本 job 缓冲的 investments 按 entity 写入 CSV 并清空 buffer。"""
        if not self._job_buffer:
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "target_files": 0,
                "investment_files": 0,
                "goal_files": 0,
            }

        grouped = self._group_investments_by_entity(self._job_buffer)
        investment_files = 0
        goal_files = 0
        investment_rows_count = 0
        goal_rows_count = 0

        for entity_id, investments in grouped.items():
            stock_investments = StockInvestments.build(entity_id, investments)
            goal_achievements = GoalAchievements.build(entity_id, investments)
            if stock_investments.rows:
                stock_investments.save(self.output_dir, append=True)
                investment_files += 1
                investment_rows_count += len(stock_investments.rows)
            if goal_achievements.rows:
                goal_achievements.save(self.output_dir, append=True)
                goal_files += 1
                goal_rows_count += len(goal_achievements.rows)

        self._job_buffer.clear()
        logger.info(
            "Wrote job CSV: dir=%s, investment_files=%d, goal_files=%d, "
            "investment_rows=%d, goal_rows=%d",
            self.output_dir,
            investment_files,
            goal_files,
            investment_rows_count,
            goal_rows_count,
        )
        return {
            "written_files": investment_files,
            "opportunities_count": investment_rows_count,
            "target_files": goal_files,
            "investment_files": investment_files,
            "goal_files": goal_files,
            "goal_rows_count": goal_rows_count,
        }

    def to_snapshot(self) -> Dict[str, Any]:
        snapshot = super().to_snapshot()
        snapshot["settings_fp"] = self.settings_fp
        snapshot["env_fp"] = self.env_fp
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> EntityBasedEnumeratorRecorder:
        base = super().from_snapshot(snapshot)
        return cls(
            output_dir=base.output_dir,
            strategy_id=base.strategy_id,
            version_id=base.version_id,
            version_dir_name=base.version_dir_name,
            settings_fp=str(snapshot.get("settings_fp") or ""),
            env_fp=str(snapshot.get("env_fp") or ""),
        )

    @staticmethod
    def _group_investments_by_entity(
        buffer: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in buffer:
            entity_id = str(entry.get("entity_id") or "").strip()
            if not entity_id:
                continue
            investment = entry.get("opportunity")
            if not isinstance(investment, dict):
                continue
            grouped.setdefault(entity_id, []).append(dict(investment))
        return grouped


__all__ = [
    "EntityBasedEnumeratorRecorder",
    "LEGACY_RUN_PRECONDITION_FILENAME",
    "LEGACY_SCOPE_STOCK_IDS_FILENAME",
]
