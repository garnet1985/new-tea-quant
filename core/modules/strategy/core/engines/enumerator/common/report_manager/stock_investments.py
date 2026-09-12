"""ReportManager.investments 写门面：EnumResult JSON 为主；CSV sidecar 暂留。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import EnumerateStore

__all__ = [
    "InvestmentsReport",
]


class InvestmentsReport:
    """每股落盘：``entities/{id}.json``；CSV 为 DEPRECATED sidecar（价格/组合未迁完前）。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    def _store(self) -> EnumerateStore:
        return EnumerateStore.at(
            self._manager.output_dir,
            version_id=str(self._manager.version_id),
        )

    def append_entity(self, entity_id: str, investments: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        """DEPRECATED: 写 ``*_stock_investments.csv`` / goals / snapshots。新路径走 JSON。"""
        return self._store().append_entity(entity_id, investments)

    def flush_buffered(self, buffer: List[Dict[str, Any]]) -> Dict[str, int]:
        if not buffer:
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "target_files": 0,
                "investment_files": 0,
                "goal_files": 0,
                "goal_rows_count": 0,
                "json_files": 0,
            }

        json_files = self._persist_enum_results(buffer)
        grouped = self._group_legacy_payloads(buffer)
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
            "json_files": json_files,
        }

    def _persist_enum_results(self, buffer: List[Dict[str, Any]]) -> int:
        grouped: Dict[str, List[Any]] = {}
        for entry in buffer:
            entity_id = str(entry.get("entity_id") or "").strip()
            if not entity_id:
                continue
            item = entry.get("investment")
            if item is None:
                item = entry.get("enum_result")
            if item is None:
                continue
            grouped.setdefault(entity_id, []).append(item)
        if not grouped:
            return 0
        manager = EnumResultsManager.at(self._manager.output_dir)
        for entity_id, items in grouped.items():
            manager.accept(entity_id, items)
        return len(manager.persist())

    @staticmethod
    def _group_legacy_payloads(buffer: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """DEPRECATED: ``opportunity`` nested dict → CSV 行模型。"""
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
