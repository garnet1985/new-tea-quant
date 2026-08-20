"""逐股资金摘要（entity_list.json）。"""
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


@dataclass
class EntityListRow:
    """单股资金摘要（对齐 UI capital grid）。"""

    entity_id: str
    stock_name: str = ""
    trade_count: int = 0
    total_profit: float = 0.0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "stock_name": self.stock_name or self.entity_id,
            "trade_count": self.trade_count,
            "total_profit": self.total_profit,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "win_rate": self.win_rate,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityListRow":
        data = raw or {}
        eid = str(data.get("entity_id") or "").strip()
        return cls(
            entity_id=eid,
            stock_name=str(data.get("stock_name") or eid),
            trade_count=int(data.get("trade_count") or 0),
            total_profit=float(data.get("total_profit") or 0.0),
            win_trades=int(data.get("win_trades") or 0),
            loss_trades=int(data.get("loss_trades") or 0),
            win_rate=float(data.get("win_rate") or 0.0),
        )


@dataclass
class EntityListReport:
    """逐股资金摘要报告稿。"""

    ENTITY_LIST_FILE = ENTITY_LIST_FILE

    strategy_key: str = ""
    version_id: int = 0
    rows: List[EntityListRow] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def build_from_trades(
        cls,
        trades: List[Any],
        *,
        strategy_key: str = "",
        version_id: int = 0,
    ) -> "EntityListReport":
        by_entity: Dict[str, Dict[str, float]] = {}
        for t in trades:
            eid = str(getattr(t, "entity_id", "") or "").strip()
            if not eid:
                continue
            bucket = by_entity.setdefault(
                eid,
                {"sells": 0.0, "profit": 0.0, "wins": 0.0, "losses": 0.0},
            )
            if not getattr(t, "is_sell", lambda: False)():
                continue
            pnl = float(getattr(t, "profit", 0.0) or 0.0)
            bucket["sells"] += 1.0
            bucket["profit"] += pnl
            if pnl > 0:
                bucket["wins"] += 1.0
            else:
                bucket["losses"] += 1.0

        rows: List[EntityListRow] = []
        for eid, b in by_entity.items():
            sells = int(b["sells"])
            wins = int(b["wins"])
            rows.append(
                EntityListRow(
                    entity_id=eid,
                    stock_name=eid,
                    trade_count=sells,
                    total_profit=round(float(b["profit"]), 2),
                    win_trades=wins,
                    loss_trades=int(b["losses"]),
                    win_rate=round((float(wins) / float(sells) * 100.0), 1)
                    if sells
                    else 0.0,
                )
            )
        rows.sort(key=lambda r: (-r.total_profit, r.entity_id))
        return cls(
            strategy_key=strategy_key,
            version_id=version_id,
            rows=rows,
            created_at=datetime.now().isoformat(),
        )

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
        print(f"{icon('green_dot')} 有成交股票 {n} 只", file=out, flush=True)
        top = self.rows[:5]
        if not top:
            return
        print(f"{icon('chart')} Top 盈亏", file=out, flush=True)
        print("  代码              盈亏", file=out, flush=True)
        for row in top:
            print(
                f"  {row.entity_id:<16}  {row.total_profit:+.2f}",
                file=out,
                flush=True,
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "rows": [row.to_dict() for row in self.rows],
            "created_at": self.created_at,
        }

    def to_ui_rows(self) -> List[Dict[str, Any]]:
        """UI capital grid rows（camelCase）。"""
        return [
            {
                "id": row.entity_id,
                "stockCode": row.entity_id,
                "stockName": row.stock_name or row.entity_id,
                "tradeCount": row.trade_count,
                "pnl": row.total_profit,
                "winRate": row.win_rate,
            }
            for row in self.rows
        ]

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntityListReport":
        data = raw or {}
        rows = [
            EntityListRow.from_dict(item)
            for item in (data.get("rows") or [])
            if isinstance(item, dict)
        ]
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            rows=rows,
            created_at=str(data.get("created_at") or ""),
        )


class EntityListReportHandle:
    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[EntityListReport] = None

    def build_from_trades(self, trades: List[Any]) -> "EntityListReportHandle":
        self._report = EntityListReport.build_from_trades(
            trades,
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self._report = EntityListReport(
                strategy_key=self._manager.strategy_key,
                version_id=self._manager.version_id,
            )
        return self._report.save(self._manager.output_dir)

    def present(self, stream: Optional[TextIO] = None) -> None:
        EntityListReport.load(self._manager.output_dir).present(stream=stream)

    @property
    def report(self) -> Optional[EntityListReport]:
        return self._report


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.report_manager.report_manager import (
        ReportManager,
    )


__all__ = ["EntityListRow", "EntityListReport", "EntityListReportHandle"]
