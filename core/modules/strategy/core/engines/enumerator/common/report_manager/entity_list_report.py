"""每股机会摘要表（entity_list.json）—— UI data grid / CMD 简报 / DB 可缓存。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.engines.shared.data_class.investment import Lifecycle
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_LIST_FILE,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.opportunity_metrics import (
    TimingDispersion,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.report_scan import (
    EnumCsvScan,
)


@dataclass
class EntityListRow:
    """单股机会摘要（对齐 UI grid）。"""

    entity_id: str
    stock_name: str = ""
    opportunities: int = 0
    completion_rate: float = 0.0
    avg_gap_days: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "stock_name": self.stock_name or self.entity_id,
            "opportunities": self.opportunities,
            "completion_rate": self.completion_rate,
            "avg_gap_days": self.avg_gap_days,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityListRow":
        data = raw or {}
        eid = str(data.get("entity_id") or "").strip()
        return cls(
            entity_id=eid,
            stock_name=str(data.get("stock_name") or eid),
            opportunities=int(data.get("opportunities") or 0),
            completion_rate=float(data.get("completion_rate") or 0.0),
            avg_gap_days=float(data.get("avg_gap_days") or 0.0),
        )


@dataclass
class EntityListReport:
    """每股摘要表报告稿（文件 / DB / presenter 同一契约）。"""

    ENTITY_LIST_FILE = ENTITY_LIST_FILE

    strategy_key: str = ""
    version_id: int = 0
    rows: List[EntityListRow] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def build_from_scan(cls, scan: EnumCsvScan) -> "EntityListReport":
        rows: List[EntityListRow] = []
        for entity_id, invs in scan.investments_by_entity.items():
            total = len(invs)
            if total <= 0:
                continue
            completed = sum(
                1 for r in invs if r.lifecycle == Lifecycle.COMPLETE.value
            )
            rows.append(
                EntityListRow(
                    entity_id=entity_id,
                    stock_name=entity_id,
                    opportunities=total,
                    completion_rate=round((completed / total) * 100.0, 1)
                    if total
                    else 0.0,
                    avg_gap_days=TimingDispersion.mean_gap_for_rows(invs),
                )
            )
        rows.sort(key=lambda r: (-r.opportunities, r.entity_id))
        return cls(
            strategy_key=scan.strategy_key,
            version_id=scan.version_id,
            rows=rows,
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def build(
        cls,
        output_dir: Path,
        *,
        strategy_key: str = "",
        version_id: int = 0,
        total_entities: Optional[int] = None,
    ) -> "EntityListReport":
        scan = EnumCsvScan.collect(
            output_dir,
            total_entities=total_entities,
            strategy_key=strategy_key,
            version_id=version_id,
        )
        return cls.build_from_scan(scan)

    @classmethod
    def load(cls, output_dir: Path) -> "EntityListReport":
        path = output_dir / cls.ENTITY_LIST_FILE
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, output_dir: Path) -> Path:
        path = output_dir / self.ENTITY_LIST_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CMD：触发股数 + Top5（全表留给 UI grid）。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        n = len(self.rows)
        CmdLayout.title.print_section(f"{icon('search')} 每股机会摘要", stream=out)
        print(f"{icon('green_dot')} 触发股票 {n} 只", file=out, flush=True)
        top = self.rows[:5]
        if not top:
            return
        CmdLayout.bar_chart.print(
            [(row.entity_id, row.opportunities) for row in top],
            title=f"{icon('chart')} Top 实体",
            width=24,
            stream=out,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "rows": [row.to_dict() for row in self.rows],
            "created_at": self.created_at,
        }

    def to_ui_dict(self) -> Dict[str, Any]:
        """UI stock_ref 形：``{ entity_id: {…} }``。"""
        return {
            row.entity_id: {
                "stock_name": row.stock_name,
                "opportunities": row.opportunities,
                "completion_rate": row.completion_rate,
                "avg_gap_days": row.avg_gap_days,
            }
            for row in self.rows
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityListReport":
        data = raw or {}
        rows_raw = data.get("rows") or []
        rows = [
            EntityListRow.from_dict(item)
            for item in rows_raw
            if isinstance(item, dict)
        ]
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            rows=rows,
            created_at=str(data.get("created_at") or ""),
        )


class EntityListReportHandle:
    """ReportManager.entity_list 门面。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[EntityListReport] = None

    def build_from_scan(self, scan: EnumCsvScan) -> "EntityListReportHandle":
        self._report = EntityListReport.build_from_scan(scan)
        return self

    def build(self, *, total_entities: Optional[int] = None) -> "EntityListReportHandle":
        self._report = EntityListReport.build(
            self._manager.output_dir,
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            total_entities=total_entities,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self.build()
        assert self._report is not None
        return self._report.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return EntityListReport.load(self._manager.output_dir).to_dict()

    def present(self, stream: Optional[TextIO] = None) -> None:
        EntityListReport.load(self._manager.output_dir).present(stream=stream)


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "EntityListRow",
    "EntityListReport",
    "EntityListReportHandle",
]
