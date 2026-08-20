"""每股价格摘要表（entity_list.json）—— UI grid / CMD / DB。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.services.artifacts import (
    ENTITY_LIST_FILE,
)
from core.modules.strategy.core.engines.price_factor.report_manager.price_metrics import (
    RoiDistribution,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_scan import (
    PriceCsvScan,
)


@dataclass
class EntityListRow:
    """单股价格摘要（对齐 UI 逐股 grid / 原 stock_ref）。"""

    entity_id: str
    stock_name: str = ""
    win_rate: float = 0.0
    avg_roi: float = 0.0
    avg_duration_in_days: float = 0.0
    expiration_ratio: float = 0.0
    total_investments: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "stock_name": self.stock_name or self.entity_id,
            "win_rate": self.win_rate,
            "avg_roi": self.avg_roi,
            "avg_duration_in_days": self.avg_duration_in_days,
            "expiration_ratio": self.expiration_ratio,
            "total_investments": self.total_investments,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityListRow":
        data = raw or {}
        eid = str(data.get("entity_id") or "").strip()
        return cls(
            entity_id=eid,
            stock_name=str(data.get("stock_name") or eid),
            win_rate=float(data.get("win_rate") or 0.0),
            avg_roi=float(data.get("avg_roi") or 0.0),
            avg_duration_in_days=float(data.get("avg_duration_in_days") or 0.0),
            expiration_ratio=float(data.get("expiration_ratio") or 0.0),
            total_investments=int(data.get("total_investments") or 0),
        )


@dataclass
class EntityListReport:
    """每股摘要表报告稿。"""

    ENTITY_LIST_FILE = ENTITY_LIST_FILE

    strategy_key: str = ""
    version_id: int = 0
    rows: List[EntityListRow] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def build_from_scan(cls, scan: PriceCsvScan) -> "EntityListReport":
        rows: List[EntityListRow] = []
        for entity_id, invs in scan.investments_by_entity.items():
            active = [r for r in invs if not r.skip_reason]
            total = len(active)
            if total <= 0:
                continue
            win = 0
            roi_sum = 0.0
            hold_sum = 0.0
            hold_n = 0
            expired = 0
            for row in active:
                result = (row.result or "").strip().lower()
                if result in {"win", "profit"} or (row.roi > 0 and row.exit_date):
                    win += 1
                roi_sum += float(row.roi or 0.0)
                if row.holding_days:
                    hold_sum += float(row.holding_days)
                    hold_n += 1
                if RoiDistribution.is_expired(row):
                    expired += 1
            rows.append(
                EntityListRow(
                    entity_id=entity_id,
                    stock_name=entity_id,
                    win_rate=round((float(win) / float(total)) * 100.0, 1),
                    avg_roi=round(roi_sum / float(total), 4),
                    avg_duration_in_days=round(hold_sum / float(hold_n), 1)
                    if hold_n
                    else 0.0,
                    expiration_ratio=round((float(expired) / float(total)) * 100.0, 1),
                    total_investments=total,
                )
            )
        rows.sort(key=lambda r: (-r.avg_roi, r.entity_id))
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
        entity_ids: Optional[List[str]] = None,
        strategy_key: str = "",
        version_id: int = 0,
    ) -> "EntityListReport":
        scan = PriceCsvScan.collect(
            output_dir,
            entity_ids=entity_ids,
            strategy_key=strategy_key,
            version_id=version_id,
        )
        return cls.build_from_scan(scan)

    @classmethod
    def load(cls, output_dir: Path) -> "EntityListReport":
        path = Path(output_dir) / cls.ENTITY_LIST_FILE
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, output_dir: Path) -> Path:
        path = Path(output_dir) / self.ENTITY_LIST_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        n = len(self.rows)
        CmdLayout.title.print_section(f"{icon('search')} 逐股样本", stream=out)
        print(f"{icon('green_dot')} 有仓股票 {n} 只", file=out, flush=True)
        top = self.rows[:5]
        if not top:
            return
        CmdLayout.bar_chart.print(
            [(row.entity_id, round(row.avg_roi * 100.0, 2)) for row in top],
            title=f"{icon('chart')} Top ROI (%)",
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
        """UI stock_ref 形：``{ entity_id: {… snake_case} }``。"""
        return {
            row.entity_id: {
                "stock_name": row.stock_name,
                "win_rate": row.win_rate,
                "avg_roi": row.avg_roi,
                "avg_duration_in_days": row.avg_duration_in_days,
                "expiration_ratio": row.expiration_ratio,
                "total_investments": row.total_investments,
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

    def build_from_scan(self, scan: PriceCsvScan) -> "EntityListReportHandle":
        self._report = EntityListReport.build_from_scan(scan)
        return self

    def build(self) -> "EntityListReportHandle":
        self._report = EntityListReport.build(
            self._manager.output_dir,
            entity_ids=list(self._manager.entity_ids),
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
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
    from core.modules.strategy.core.engines.price_factor.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "EntityListRow",
    "EntityListReport",
    "EntityListReportHandle",
]
