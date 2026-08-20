"""用户钩子回调入参：StrategyContext 壳 + 嵌套只读块。

本文件:
- StrategyInfo / StrategyData: 只读 dataclass
- StrategyContext: strategy + settings + data + custom / captures
  边界: 只读块由引擎组装；用户写口为 remember/recall/forget 与 capture
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


def _freeze_map(raw: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return MappingProxyType(dict(raw or {}))


@dataclass(frozen=True)
class StrategyInfo:
    """策略身份（只读）。"""

    key: str
    path: str = ""


@dataclass(frozen=True)
class StrategyData:
    """运行数据（只读）。

    - ``has_opportunity``：``items`` 为单实体 DataKey→rows；可带 ``entity_id`` / ``entity_info``
    - ``on_calendar_asof``：``by_entity`` 为 entity_id→当日 payload；``calendar`` 为日历元数据
    """

    now: str = ""
    stock_list: Tuple[str, ...] = ()
    entity_id: str = ""
    entity_info: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    items: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    by_entity: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    calendar: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    opportunity: Optional[Opportunity] = None

    @staticmethod
    def build(
        *,
        now: str = "",
        stock_list: Optional[List[str]] = None,
        entity_id: str = "",
        entity_info: Optional[Mapping[str, Any]] = None,
        items: Optional[Mapping[str, Any]] = None,
        by_entity: Optional[Mapping[str, Any]] = None,
        calendar: Optional[Mapping[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
    ) -> "StrategyData":
        return StrategyData(
            now=str(now or "").strip(),
            stock_list=tuple(str(x).strip() for x in (stock_list or []) if str(x).strip()),
            entity_id=str(entity_id or "").strip(),
            entity_info=_freeze_map(entity_info),
            items=_freeze_map(items),
            by_entity=_freeze_map(by_entity),
            calendar=_freeze_map(calendar),
            opportunity=opportunity,
        )

    def items_with_meta(self) -> Dict[str, Any]:
        """浅拷贝 items，并附带 now / stock_list（供 helpers 只读消费）。"""
        out = dict(self.items)
        out["now"] = self.now
        out["stock_list"] = list(self.stock_list)
        return out


@dataclass
class StrategyContext:
    """钩子回调入参壳：只读块 + ``custom``（remember）+ 归因袋（capture）。"""

    strategy: StrategyInfo
    settings: StrategySettings
    data: StrategyData
    custom: Dict[str, Any] = field(default_factory=dict)
    _cached_settings_dict: Optional[Dict[str, Any]] = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _captures: Dict[str, Any] = field(
        default_factory=dict,
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def base_data_key(self) -> str:
        return self.settings.data.base_data_key

    def effective_settings_dict(self) -> Dict[str, Any]:
        """settings 的 dict 视图（缓存；热路径勿每 tick 调 ``settings.to_dict()``）。"""
        cached = self._cached_settings_dict
        if cached is None:
            cached = self.settings.to_dict()
            self._cached_settings_dict = cached
        return cached

    def remember(self, key: str, value: Any) -> None:
        """写入本次回测内存袋（``custom``）；任务结束即释放。"""
        self.custom[str(key)] = value

    def recall(self, key: str, default: Any = None) -> Any:
        """读取 ``remember`` 的值；缺 key 返回 ``default``。"""
        return self.custom.get(str(key), default)

    def forget(self, key: str) -> None:
        """删除 ``remember`` 的值；缺 key 静默。"""
        self.custom.pop(str(key), None)

    def capture(self, key: str, value: Any) -> None:
        """记录本笔命中的逻辑层输入（归因）；不进 ``custom``。"""
        self._captures[str(key)] = value

    def clear_captures(self) -> None:
        """引擎：每次 ``has_opportunity`` 前清空归因袋。"""
        self._captures.clear()

    def take_captures(self) -> Dict[str, Any]:
        """引擎：取出并清空归因袋。"""
        out = dict(self._captures)
        self._captures.clear()
        return out

    def with_data(self, data: StrategyData) -> "StrategyContext":
        """引擎：换 data，共享 ``custom`` / captures 与 settings 缓存。"""
        ctx = StrategyContext(
            strategy=self.strategy,
            settings=self.settings,
            data=data,
            custom=self.custom,
        )
        ctx._cached_settings_dict = self._cached_settings_dict
        ctx._captures = self._captures
        return ctx

    def refill(
        self,
        *,
        now: str,
        items: Optional[Mapping[str, Any]] = None,
        calendar: Optional[Mapping[str, Any]] = None,
        entity_id: Optional[str] = None,
        entity_info: Optional[Mapping[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
    ) -> "StrategyContext":
        """热路径：就地替换 ``data``（保留 strategy / settings / custom / captures）。"""
        stock_list = list(self.data.stock_list)
        if not stock_list:
            raise ValueError("StrategyContext.refill 要求已 assemble（含 stock_list）")
        self.data = StrategyData.build(
            now=now,
            stock_list=stock_list,
            entity_id=self.data.entity_id if entity_id is None else entity_id,
            entity_info=self.data.entity_info if entity_info is None else entity_info,
            items=items,
            by_entity=self.data.by_entity,
            calendar=self.data.calendar if calendar is None else calendar,
            opportunity=opportunity,
        )
        return self

    @classmethod
    def assemble(
        cls,
        *,
        strategy_key: str,
        settings: StrategySettings,
        stock_list: List[str],
        strategy_path: str = "",
        entity_id: str = "",
        entity_info: Optional[Mapping[str, Any]] = None,
        custom: Optional[Dict[str, Any]] = None,
    ) -> "StrategyContext":
        """0→1：建立壳（尚无当日 items / by_entity）。"""
        return cls(
            strategy=StrategyInfo(
                key=str(strategy_key or "").strip(),
                path=str(strategy_path or "").strip(),
            ),
            settings=settings,
            data=StrategyData.build(
                stock_list=stock_list,
                entity_id=entity_id,
                entity_info=entity_info,
            ),
            custom=dict(custom or {}),
        )

    @classmethod
    def fill(
        cls,
        base: "StrategyContext",
        *,
        now: str,
        items: Optional[Mapping[str, Any]] = None,
        by_entity: Optional[Mapping[str, Any]] = None,
        calendar: Optional[Mapping[str, Any]] = None,
        entity_id: Optional[str] = None,
        entity_info: Optional[Mapping[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
    ) -> "StrategyContext":
        """1→1：基于 base 填当日只读 data（共享 custom / captures）。"""
        if base is None:
            raise ValueError("StrategyContext.fill 要求非空 base")
        stock_list = list(base.data.stock_list)
        if not stock_list:
            raise ValueError("StrategyContext.fill 要求 base 已 assemble（含 stock_list）")
        return base.with_data(
            StrategyData.build(
                now=now,
                stock_list=stock_list,
                entity_id=base.data.entity_id if entity_id is None else entity_id,
                entity_info=base.data.entity_info if entity_info is None else entity_info,
                items=items,
                by_entity=by_entity if by_entity is not None else base.data.by_entity,
                calendar=calendar if calendar is not None else base.data.calendar,
                opportunity=opportunity,
            )
        )


__all__ = [
    "StrategyContext",
    "StrategyData",
    "StrategyInfo",
]
