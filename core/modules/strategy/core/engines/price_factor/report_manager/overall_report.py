"""价格回测 ``overall_report.json`` 跨 entity 汇总。

本文件:
- OverallSummary / OverallReport: 从 EntityInvestments 聚合 win_rate、avg_roi 等
  边界: 负责 summary 计算与写盘；不负责单股 CSV 回放
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from core.modules.strategy.core.engines.price_factor.report_manager.investments import (
    EntityInvestments,
    PriceInvestmentRow,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_consts import (
    ReportPaths,
)


@dataclass
class OverallSummary:
    """跨 entity 价格回测汇总。"""

    total_investments: int = 0
    total_completed: int = 0
    total_open: int = 0
    total_win: int = 0
    total_loss: int = 0
    total_skipped: int = 0
    win_rate: float = 0.0
    avg_roi: float = 0.0
    avg_holding_days: float = 0.0
    avg_holding_trading_days: float = 0.0
    entities_with_investments: int = 0
    entity_count: int = 0
    period: Dict[str, str] = field(default_factory=dict)
    enum_version_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_investments": self.total_investments,
            "total_completed": self.total_completed,
            "total_open": self.total_open,
            "total_win": self.total_win,
            "total_loss": self.total_loss,
            "total_skipped": self.total_skipped,
            "win_rate": self.win_rate,
            "avg_roi": self.avg_roi,
            "avg_holding_days": self.avg_holding_days,
            "avg_holding_trading_days": self.avg_holding_trading_days,
            "entities_with_investments": self.entities_with_investments,
            "entity_count": self.entity_count,
            "period": dict(self.period or {}),
            "enum_version_id": self.enum_version_id,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallSummary":
        data = raw or {}
        period = data.get("period") if isinstance(data.get("period"), dict) else {}
        return cls(
            total_investments=int(data.get("total_investments") or 0),
            total_completed=int(data.get("total_completed") or 0),
            total_open=int(data.get("total_open") or 0),
            total_win=int(data.get("total_win") or 0),
            total_loss=int(data.get("total_loss") or 0),
            total_skipped=int(data.get("total_skipped") or 0),
            win_rate=float(data.get("win_rate") or 0.0),
            avg_roi=float(data.get("avg_roi") or 0.0),
            avg_holding_days=float(data.get("avg_holding_days") or 0.0),
            avg_holding_trading_days=float(data.get("avg_holding_trading_days") or 0.0),
            entities_with_investments=int(data.get("entities_with_investments") or 0),
            entity_count=int(data.get("entity_count") or 0),
            period={
                "start_date": str(period.get("start_date") or "").strip(),
                "end_date": str(period.get("end_date") or "").strip(),
            },
            enum_version_id=str(data.get("enum_version_id") or "").strip(),
        )

    @classmethod
    def from_investments(
        cls,
        by_entity: Dict[str, List[PriceInvestmentRow]],
        *,
        entity_count: int,
        period: Dict[str, str],
        enum_version_id: str,
    ) -> "OverallSummary":
        total = 0
        completed = 0
        open_count = 0
        win = 0
        loss = 0
        skipped = 0
        roi_sum = 0.0
        roi_n = 0
        hold_sum = 0.0
        hold_n = 0
        hold_td_sum = 0.0
        hold_td_n = 0
        with_inv = 0

        for rows in by_entity.values():
            if not rows:
                continue
            with_inv += 1
            for row in rows:
                total += 1
                if row.skip_reason:
                    skipped += 1
                    continue
                result = (row.result or "").strip().lower()
                lifecycle = (row.lifecycle or "").strip().lower()
                if result in {"win", "profit"} or (row.roi > 0 and row.exit_date):
                    win += 1
                    completed += 1
                elif result in {"loss"} or (row.roi < 0 and row.exit_date):
                    loss += 1
                    completed += 1
                elif row.exit_date:
                    completed += 1
                elif lifecycle in {"open", "holding", "active"} or not row.exit_date:
                    open_count += 1

                if row.exit_date or row.roi != 0.0:
                    roi_sum += float(row.roi)
                    roi_n += 1
                if row.holding_days:
                    hold_sum += float(row.holding_days)
                    hold_n += 1
                if row.holding_trading_days:
                    hold_td_sum += float(row.holding_trading_days)
                    hold_td_n += 1

        decided = win + loss
        return cls(
            total_investments=total,
            total_completed=completed,
            total_open=open_count,
            total_win=win,
            total_loss=loss,
            total_skipped=skipped,
            win_rate=(float(win) / float(decided) * 100.0) if decided else 0.0,
            avg_roi=(roi_sum / float(roi_n)) if roi_n else 0.0,
            avg_holding_days=(hold_sum / float(hold_n)) if hold_n else 0.0,
            avg_holding_trading_days=(hold_td_sum / float(hold_td_n)) if hold_td_n else 0.0,
            entities_with_investments=with_inv,
            entity_count=int(entity_count),
            period=dict(period or {}),
            enum_version_id=str(enum_version_id or "").strip(),
        )


class OverallReport:
    """读写 ``overall_report.json``。"""

    @classmethod
    def build(
        cls,
        output_dir: Path,
        *,
        entity_ids: Sequence[str],
        period: Dict[str, str],
        enum_version_id: str,
    ) -> Dict[str, Any]:
        by_entity = EntityInvestments.load_all(output_dir, entity_ids)
        summary = OverallSummary.from_investments(
            by_entity,
            entity_count=len(list(entity_ids)),
            period=period,
            enum_version_id=enum_version_id,
        )
        return {
            "summary": summary.to_dict(),
            "entity_summaries": [
                {
                    "entity_id": eid,
                    "investment_count": len(by_entity.get(eid) or []),
                }
                for eid in entity_ids
                if str(eid or "").strip()
            ],
        }

    @classmethod
    def save_payload(cls, output_dir: Path, payload: Dict[str, Any]) -> Path:
        path = ReportPaths.overall_report_path(output_dir)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    @classmethod
    def build_and_save(
        cls,
        output_dir: Path,
        *,
        entity_ids: Sequence[str],
        period: Dict[str, str],
        enum_version_id: str,
    ) -> Dict[str, Any]:
        payload = cls.build(
            output_dir,
            entity_ids=entity_ids,
            period=period,
            enum_version_id=enum_version_id,
        )
        cls.save_payload(output_dir, payload)
        return payload

    @classmethod
    def load(cls, output_dir: Path) -> Dict[str, Any]:
        path = ReportPaths.overall_report_path(output_dir)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["OverallReport", "OverallSummary"]
