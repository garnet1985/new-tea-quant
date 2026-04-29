#!/usr/bin/env python3
"""枚举报告数据类。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.components.simulator.base.report_base import ReportBase


@dataclass
class EnumReport(ReportBase):
    strategy_name: str
    version_id: int
    version_dir: str
    opportunity_count: int
    success_stocks: int
    failed_stocks: int
    total_stocks: int
    completed_count: int
    unfinished_count: int
    completion_rate: float

    @classmethod
    def from_run_summary(
        cls,
        strategy_name: str,
        version_id: int,
        version_dir: str,
        opportunity_count: int,
        success_stocks: int,
        failed_stocks: int,
        completed_count: int = 0,
        unfinished_count: int = 0,
    ) -> "EnumReport":
        total_stocks = max(int(success_stocks) + int(failed_stocks), 0)
        completion_rate = (
            float(completed_count) / float(opportunity_count)
            if opportunity_count > 0
            else 0.0
        )
        return cls(
            strategy_name=strategy_name,
            version_id=int(version_id),
            version_dir=str(version_dir),
            opportunity_count=max(int(opportunity_count), 0),
            success_stocks=max(int(success_stocks), 0),
            failed_stocks=max(int(failed_stocks), 0),
            total_stocks=total_stocks,
            completed_count=max(int(completed_count), 0),
            unfinished_count=max(int(unfinished_count), 0),
            completion_rate=max(completion_rate, 0.0),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnumReport":
        return cls(
            strategy_name=str(data.get("strategy_name", "")),
            version_id=int(data.get("version_id", 0) or 0),
            version_dir=str(data.get("version_dir", "")),
            opportunity_count=int(data.get("opportunity_count", 0) or 0),
            success_stocks=int(data.get("success_stocks", 0) or 0),
            failed_stocks=int(data.get("failed_stocks", 0) or 0),
            total_stocks=int(data.get("total_stocks", 0) or 0),
            completed_count=int(data.get("completed_count", 0) or 0),
            unfinished_count=int(data.get("unfinished_count", 0) or 0),
            completion_rate=float(data.get("completion_rate", 0.0) or 0.0),
        )

    def to_console_lines(self) -> List[str]:
        return [
            f"策略: {self.strategy_name}",
            f"版本: {self.version_id} ({self.version_dir})",
            f"机会数: {self.opportunity_count}",
            f"成功/失败股票数: {self.success_stocks}/{self.failed_stocks}",
            f"完成/未完成机会数: {self.completed_count}/{self.unfinished_count}",
            f"完成率: {self.completion_rate * 100:.2f}%",
        ]

