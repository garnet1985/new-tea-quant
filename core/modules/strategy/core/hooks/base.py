"""用户 StrategyHooks 抽象基类（userspace 继承实现）。

本文件:
- StrategyHooks: scan / asof / portfolio 等 hook 声明与默认实现
  边界: 定义用户扩展点；不负责加载、StrategyContext 组装或 BE 调度
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from core.modules.strategy.core.engines.shared.data_class import (
    CalendarAsOfResult,
    Opportunity,
)
from core.modules.strategy.core.hooks.hook_params import StrategyContext


class StrategyHooks(ABC):
    """用户策略 hooks 基类。"""

    def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
        """Calendar as-of hook（slice_based 使用；entity_based 默认空）。"""
        return CalendarAsOfResult(as_of_date=str(ctx.data.now or ""), stocks=[])

    def calendar_asof_needs_by_entity(self, ctx: StrategyContext) -> bool:
        """``on_calendar_asof`` 是否需要 ``ctx.data.by_entity`` 市况包。

        返回 False 时，enumerator 可用空 ``by_entity`` 调用 asof，跳过全宇宙组包。
        若仍返回非空 ``stocks``，引擎会回退为全量组包再调一次。
        默认 True（安全）；纯日历门闩 / null 基准应覆盖为 False。
        """
        _ = ctx
        return True

    def on_before_scan(self, ctx: StrategyContext) -> None:
        """scan 前 hook。"""
        return None

    @abstractmethod
    def scan_opportunity(self, ctx: StrategyContext) -> Optional[Opportunity]:
        """扫描机会（用户必须实现）。"""
        pass

    def on_after_scan(self, ctx: StrategyContext) -> None:
        """scan 后 hook。"""
        return None

    def on_pick_portfolio_member(
        self, ctx: StrategyContext
    ) -> Sequence[Union[Opportunity, str]]:
        """挑选当日要进入组合的 members（可多个）。

        ``ctx.data.items["opportunities"]``：当日可用机会（已 ``to_opportunity``，无结果字段）。
        ``ctx.data.items["account"]``：容量快照（``held_entity_ids`` / ``remaining_slots`` 等）。

        返回选中的 ``Opportunity`` 列表，或 ``opportunity_id`` 字符串列表。
        **不返回仓位 sizing**（shares/weight 由 AllocationStrategy 按配置计算）。

        未 override 时，portfolio ``EnterSelection`` 直接用 ``EntrySelector``
        （顺序 + ``max_portfolio_size`` 剩余槽位），不会调用本默认实现。
        """
        return []

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
        from core.infra.utils import Utils

        return Utils.math.deterministic_unit_float(*key_parts)

    def build_opportunity(
        self,
        ctx: StrategyContext,
        record_of_today: Dict[str, Any],
        *,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Opportunity:
        stock_info = dict(ctx.data.entity_info) if ctx.data.entity_info else {}
        return Opportunity(
            stock=stock_info,
            record_of_today=record_of_today,
            extra_fields=extra_fields,
        )


__all__ = ["StrategyHooks"]
