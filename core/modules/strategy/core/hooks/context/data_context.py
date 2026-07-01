"""用户 hook 侧 DataContext — 策略决策所需的业务数据。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.data_classes.opportunity import Opportunity


class _HookDataStore:
    """hook 数据视图底层 store（模块内使用，不对外 export）。"""

    __slots__ = ("_store",)

    def __init__(self, store: Optional[Dict[str, Any]] = None) -> None:
        self._store: Dict[str, Any] = dict(store or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._store[key]

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def keys(self) -> Iterator[str]:
        return iter(self._store.keys())

    def to_dict(self) -> Dict[str, Any]:
        return deepcopy(self._store)

    def update(self, mapping: Dict[str, Any]) -> None:
        self._store.update(mapping)


@dataclass
class DataContext:
    """用户 hooks 唯一需要的 context。

    数据访问：``ctx.data.get("stock_list")``、``ctx.get("now")`` 等。
    不含 job_payload、data_manager、进度、profiler 等运行时内部对象。
    """

    strategy_name: str
    settings: StrategySettings

    data: _HookDataStore = field(default_factory=_HookDataStore)

    entity_id: Optional[str] = None
    entity_info: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)
    opportunity: Optional[Opportunity] = None
    calendar: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def effective_settings_dict(self) -> Dict[str, Any]:
        return self.settings.to_dict()

    @classmethod
    def assemble(
        cls,
        *,
        strategy_name: str,
        settings: StrategySettings,
        stock_list: List[str],
        entity_id: Optional[str] = None,
        entity_info: Optional[Dict[str, Any]] = None,
        now: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
        calendar: Optional[Dict[str, Any]] = None,
    ) -> DataContext:
        """worker / engine 组装 hook context（原 factory 职责）。"""
        store: Dict[str, Any] = {"stock_list": list(stock_list)}
        if now is not None:
            store["now"] = now
        if data:
            store.update(data)

        hook_data = _HookDataStore(store)
        return cls(
            strategy_name=strategy_name,
            settings=settings,
            data=hook_data,
            entity_id=entity_id,
            entity_info=dict(entity_info or {}),
            extra=dict(extra) if extra is not None else {},
            opportunity=opportunity,
            calendar=dict(calendar or {}),
        )


__all__ = ["DataContext"]
