"""用户钩子回调入参：StrategyContext 壳 + 嵌套只读块。

本文件:
- StrategyInfo / StrategyData: 只读 dataclass
- StrategyContext: strategy + settings + data + custom（custom 为可写 dict）
  边界: 用户可见四块；引擎用 assemble / fill / refill / with_* 组装，不向用户暴露写 API
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

    - ``scan_opportunity``：``items`` 为单实体 DataKey→rows；可带 ``entity_id`` / ``entity_info``
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
    """钩子回调入参壳：只读块 + 唯一可写 ``custom``。"""

    strategy: StrategyInfo
    settings: StrategySettings
    data: StrategyData
    custom: Dict[str, Any] = field(default_factory=dict)

    @property
    def base_data_key(self) -> str:
        return self.settings.data.base_data_key

    def with_data(self, data: StrategyData) -> "StrategyContext":
        """引擎：换 data，共享同一 ``custom`` dict。"""
        return StrategyContext(
            strategy=self.strategy,
            settings=self.settings,
            data=data,
            custom=self.custom,
        )

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
        """热路径：就地替换 ``data``（保留 strategy / settings / custom）。"""
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
        """1→1：基于 base 填当日只读 data（共享 custom）。"""
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
