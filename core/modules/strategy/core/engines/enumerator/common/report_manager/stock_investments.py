"""ReportManager.investments 写门面（委托 simulation_output CSV 模型）。

本文件:
- InvestmentsReport: worker buffer → 每股 CSV 追加
  边界: 仅绑 ReportManager；行模型在 simulation_output.investment_csv
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.simulation_output import (
    GoalAchievementCsv,
    InvestmentRow,
    EntityInvestmentCsv,
)

__all__ = [
    "InvestmentsReport",
    "InvestmentRow",
    "EntityInvestmentCsv",
    "GoalAchievementCsv",
]


class InvestmentsReport:
    """ReportManager.investments 门面：每股 CSV 追加写入。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    def append_entity(self, entity_id: str, investments: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        stock_investments = EntityInvestmentCsv.build(entity_id, investments)
        goal_achievements = GoalAchievementCsv.build(entity_id, investments)
        investment_files = 0
        goal_files = 0
        investment_rows = 0
        goal_rows = 0
        if stock_investments.rows:
            stock_investments.save(self._manager.output_dir, append=True)
            investment_files = 1
            investment_rows = len(stock_investments.rows)
        if goal_achievements.rows:
            goal_achievements.save(self._manager.output_dir, append=True)
            goal_files = 1
            goal_rows = len(goal_achievements.rows)
        return {
            "investment_files": investment_files,
            "goal_files": goal_files,
            "investment_rows": investment_rows,
            "goal_rows": goal_rows,
        }

    def flush_buffered(self, buffer: List[Dict[str, Any]]) -> Dict[str, int]:
        if not buffer:
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "target_files": 0,
                "investment_files": 0,
                "goal_files": 0,
                "goal_rows_count": 0,
            }

        grouped = self._group_by_entity(buffer)
        investment_files = 0
        goal_files = 0
        investment_rows_count = 0
        goal_rows_count = 0

        for entity_id, investments in grouped.items():
            stats = self.append_entity(entity_id, investments)
            investment_files += stats["investment_files"]
            goal_files += stats["goal_files"]
            investment_rows_count += stats["investment_rows"]
            goal_rows_count += stats["goal_rows"]

        return {
            "written_files": investment_files,
            "opportunities_count": investment_rows_count,
            "target_files": goal_files,
            "investment_files": investment_files,
            "goal_files": goal_files,
            "goal_rows_count": goal_rows_count,
        }

    @staticmethod
    def _group_by_entity(buffer: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
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


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )
