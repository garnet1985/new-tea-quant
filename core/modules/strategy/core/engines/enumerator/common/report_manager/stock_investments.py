"""ReportManager.investments 写门面（委托 ArtifactStore）。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, TYPE_CHECKING

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

__all__ = [
    "InvestmentsReport",
]


class InvestmentsReport:
    """ReportManager.investments 门面：每股 CSV 追加写入。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    def _store(self) -> ArtifactStore:
        return ArtifactStore.at(
            self._manager.output_dir,
            kind=SimulateKind.ENUMERATE,
            version_id=str(self._manager.version_id),
        )

    def append_entity(self, entity_id: str, investments: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        return self._store().append_enum_entity(entity_id, investments)

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
