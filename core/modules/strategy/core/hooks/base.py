"""Strategy hooks 基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.modules.strategy.core.engines.shared.data_classes import CalendarAsOfResult, Opportunity
from core.modules.strategy.core.hooks.context import DataContext


class StrategyHooks(ABC):
    """用户策略 hooks 基类。"""

    def on_entity_init(self, ctx: DataContext) -> None:
        """实体级初始化（可选）。"""
        return None

    def on_calendar_asof(self, ctx: DataContext) -> CalendarAsOfResult:
        """Calendar as-of hook（slice_based 使用；entity_based 默认空）。"""
        return CalendarAsOfResult(as_of_date=str(ctx.get("now") or ""), stocks=[])

    def on_before_scan(self, ctx: DataContext) -> None:
        """scan 前 hook。"""
        return None

    @abstractmethod
    def scan_opportunity(self, ctx: DataContext) -> Optional[Opportunity]:
        """扫描机会（用户必须实现）。"""
        pass

    def on_after_scan(self, ctx: DataContext) -> None:
        """scan 后 hook。"""
        return None

    # ── scan 辅助原语 ──

    @staticmethod
    def get_record_of_today(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        klines = data.get("klines") or []
        return klines[-1] if klines else None

    def build_opportunity(
        self,
        ctx: DataContext,
        record_of_today: Dict[str, Any],
        *,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Opportunity:
        stock_info = dict(ctx.entity_info) if ctx.entity_info else {}
        return Opportunity(
            stock=stock_info,
            record_of_today=record_of_today,
            extra_fields=extra_fields,
        )


__all__ = ["StrategyHooks"]
