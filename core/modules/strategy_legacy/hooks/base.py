#!/usr/bin/env python3
"""Strategy hooks — user-facing extension API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfResult,
)

from .types import StrategyHookContext


class StrategyHooks(ABC):
    """用户策略钩子基类；编排逻辑由 framework runner 注入调用。"""

    # ── 主进程：整次 run ──

    def on_run_start(self, ctx: StrategyHookContext) -> None:
        return None

    def on_run_finish(self, ctx: StrategyHookContext) -> None:
        return None

    # ── 主进程：调度 batch ──

    def on_batch_start(self, ctx: StrategyHookContext) -> None:
        return None

    def on_batch_finish(self, ctx: StrategyHookContext) -> None:
        return None

    # ── 子进程：单 entity job ──

    def on_entity_init(self, ctx: StrategyHookContext) -> None:
        return None

    # ── scan / simulate 内 ──

    def on_before_scan(self, ctx: StrategyHookContext) -> None:
        return None

    @abstractmethod
    def scan_opportunity(self, ctx: StrategyHookContext) -> Optional[Opportunity]:
        pass

    def on_after_scan(self, ctx: StrategyHookContext) -> None:
        return None

    # ── calendar_slice ──

    def on_calendar_asof(self, ctx: StrategyHookContext) -> CalendarAsOfResult:
        calendar = ctx.calendar
        if calendar is None:
            return CalendarAsOfResult(selected_stock_ids=[])
        return CalendarAsOfResult(selected_stock_ids=list(calendar.stocks.keys()))

    # ── price_factor ──

    def on_price_factor_before_process_stock(self, ctx: StrategyHookContext) -> None:
        return None

    def on_price_factor_after_process_stock(self, ctx: StrategyHookContext) -> Dict[str, Any]:
        pf = ctx.price_factor
        if pf is None or pf.stock_summary is None:
            return {}
        return dict(pf.stock_summary)

    def on_price_factor_opportunity_trigger(self, ctx: StrategyHookContext) -> Dict[str, Any]:
        pf = ctx.price_factor
        if pf is None or pf.opportunity_row is None:
            return {}
        return dict(pf.opportunity_row)

    def on_price_factor_target_hit(self, ctx: StrategyHookContext) -> Dict[str, Any]:
        pf = ctx.price_factor
        if pf is None or pf.target_row is None:
            return {}
        return dict(pf.target_row)

    # ── scan 辅助原语 ──

    @staticmethod
    def get_record_of_today(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        klines = data.get("klines") or []
        return klines[-1] if klines else None

    @staticmethod
    def signal_date(record_of_today: Dict[str, Any]) -> str:
        return str(record_of_today["date"])

    @staticmethod
    def core_int(settings: Dict[str, Any], key: str) -> int:
        return int(settings["core"][key])

    @staticmethod
    def core_float(
        settings: Dict[str, Any],
        key: str,
        *,
        clamp: Optional[Tuple[float, float]] = None,
    ) -> float:
        value = float(settings["core"][key])
        if clamp is None:
            return value
        low, high = clamp
        return max(low, min(high, value))

    def build_opportunity(
        self,
        ctx: StrategyHookContext,
        record_of_today: Dict[str, Any],
        *,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Opportunity:
        stock_info = {}
        if ctx.entity is not None:
            stock_info = dict(ctx.entity.stock_info)
        return Opportunity(
            stock=stock_info,
            record_of_today=record_of_today,
            extra_fields=extra_fields,
        )

    @staticmethod
    def deterministic_roll(*key_parts: Any) -> float:
        from core.utils.math.deterministic_random import deterministic_unit_float

        return deterministic_unit_float(*key_parts)


__all__ = ["StrategyHooks"]
