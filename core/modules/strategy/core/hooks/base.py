"""Strategy hooks 基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity
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
    def get_record_of_today(
        data: Dict[str, Any],
        *,
        base_data_key: str,
    ) -> Optional[Dict[str, Any]]:
        rows = data.get(base_data_key) or []
        return rows[-1] if rows else None

    @staticmethod
    def signal_date(record_of_today: Dict[str, Any]) -> str:
        if "date" not in record_of_today:
            raise ValueError("record_of_today 缺少 date")
        return str(record_of_today["date"])

    @staticmethod
    def core_int(settings: Dict[str, Any], key: str) -> int:
        core = settings.get("core")
        if not isinstance(core, dict) or key not in core:
            raise ValueError(f"settings.core 缺少 {key!r}")
        return int(core[key])

    @staticmethod
    def core_float(
        settings: Dict[str, Any],
        key: str,
        *,
        clamp: Optional[Tuple[float, float]] = None,
    ) -> float:
        core = settings.get("core")
        if not isinstance(core, dict) or key not in core:
            raise ValueError(f"settings.core 缺少 {key!r}")
        value = float(core[key])
        if clamp is None:
            return value
        low, high = clamp
        return max(low, min(high, value))

    @staticmethod
    def deterministic_roll(*key_parts: Any) -> float:
        from core.utils.math.deterministic_random import deterministic_unit_float

        return deterministic_unit_float(*key_parts)

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
