"""用户 StrategyHooks 抽象基类（userspace 继承实现）。

本文件:
- StrategyHooks: scan / asof / portfolio 等 hook 声明与默认实现
  边界: 定义用户扩展点；不负责加载、DataContext 组装或 BE 调度
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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

    def on_pick_portfolio_member(
        self, ctx: DataContext
    ) -> Sequence[Union[Opportunity, str]]:
        """挑选当日要进入组合的 members（可多个）。

        ``ctx.get("opportunities")``：当日可用机会（已 ``to_opportunity``，无结果字段）。
        ``ctx.get("account")``：容量快照（``held_entity_ids`` / ``remaining_slots`` 等）。

        返回选中的 ``Opportunity`` 列表，或 ``opportunity_id`` 字符串列表。
        **不返回仓位 sizing**（shares/weight 由 AllocationStrategy 按配置计算）。

        未 override 时，引擎用 ``EntrySelector``（顺序 + ``max_portfolio_size`` 剩余槽位）。
        """
        from core.modules.strategy.core.engines.portfolio.enter_selection import (
            EntrySelector,
        )

        opps = ctx.get("opportunities")
        if not isinstance(opps, list):
            return []
        account = ctx.get("account") if isinstance(ctx.get("account"), dict) else {}
        max_size = int(account.get("max_portfolio_size") or 0)
        if max_size <= 0:
            try:
                max_size = int(ctx.settings.portfolio.allocation.max_portfolio_size)
            except Exception:
                max_size = 10
        held = {
            str(x or "").strip()
            for x in (account.get("held_entity_ids") or [])
            if str(x or "").strip()
        }
        return EntrySelector(max_portfolio_size=max_size).pick(
            opps, held_entity_ids=held
        )

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
