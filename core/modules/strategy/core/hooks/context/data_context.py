"""用户 hook 侧 DataContext — 策略决策所需的业务数据。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, TypeVar

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

_ContextT = TypeVar("_ContextT", bound="DataContext")


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

    生命周期：
    - ``assemble``：0→1，建立结构（我是谁、配置、跨日 extra），不含当日 now/data。
    - ``fill``：1→1，在已有结构上填入当日 now/data 等，生成 hook 快照。

    数据访问：``ctx.data.get("stock.kline.daily")``、``ctx.get("now")`` 等；键与 ``DataKey.value`` 一致。
    不含 job_payload、data_manager、进度、profiler 等运行时内部对象。
    """

    strategy_name: str
    settings: StrategySettings
    base_data_key: str = ""

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
        extra: Optional[Dict[str, Any]] = None,
    ) -> _ContextT:
        """0→1：建立 hook context 结构，不含当日 now/data。"""
        settings_dict = settings.to_dict()
        data_cfg = StrategyDataConfig(settings_dict)
        base_data_key = str(data_cfg.normalize_base(data_cfg.base)["data_key"])
        store: Dict[str, Any] = {"stock_list": list(stock_list)}
        return cls(
            strategy_name=strategy_name,
            settings=settings,
            base_data_key=base_data_key,
            data=_HookDataStore(store),
            entity_id=entity_id,
            entity_info=dict(entity_info or {}),
            extra=dict(extra) if extra is not None else {},
        )

    @classmethod
    def fill(
        cls,
        base: DataContext,
        *,
        now: str,
        data: Optional[Dict[str, Any]] = None,
        calendar: Optional[Dict[str, Any]] = None,
        opportunity: Optional[Opportunity] = None,
        entity_id: Optional[str] = None,
        entity_info: Optional[Dict[str, Any]] = None,
    ) -> _ContextT:
        """1→1：在已 assemble 的 base 上填入当日视图，生成 hook 快照。"""
        if base is None:
            raise ValueError("DataContext.fill 要求非空 base（须先 assemble）")
        if not isinstance(base, cls):
            raise ValueError(
                f"DataContext.fill 要求 base 与 {cls.__name__} 同类，"
                f"实际 {type(base).__name__}"
            )
        stock_list = base.get("stock_list")
        if not isinstance(stock_list, list):
            raise ValueError("DataContext.fill 要求 base 已通过 assemble 建立（含 stock_list）")

        store: Dict[str, Any] = {"stock_list": list(stock_list), "now": now}
        if data:
            store.update(data)

        return cls(
            strategy_name=base.strategy_name,
            settings=base.settings,
            base_data_key=base.base_data_key,
            data=_HookDataStore(store),
            entity_id=entity_id if entity_id is not None else base.entity_id,
            entity_info=dict(entity_info) if entity_info is not None else base.entity_info,
            extra=base.extra,
            opportunity=opportunity,
            calendar=dict(calendar) if calendar is not None else {},
        )


__all__ = ["DataContext"]
