"""ReportManager.investments 写门面：每股 ``entities/{id}.json``。"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)

__all__ = [
    "InvestmentsReport",
]


class InvestmentsReport:
    """每股落盘：``entities/{id}.json``（EnumResult）。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    def flush_buffered(self, buffer: List[Dict[str, Any]]) -> Dict[str, int]:
        if not buffer:
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "json_files": 0,
            }

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
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "json_files": 0,
            }

        manager = EnumResultsManager.at(self._manager.output_dir)
        opportunities_count = 0
        for entity_id, items in grouped.items():
            manager.accept(entity_id, items)
            opportunities_count += len(items)
        json_files = len(manager.persist())
        return {
            "written_files": json_files,
            "opportunities_count": opportunities_count,
            "json_files": json_files,
        }


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )
