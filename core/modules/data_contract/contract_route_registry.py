#!/usr/bin/env python3
"""
DataKey -> Contract 工厂注册表（与 DataContractManager 解耦）。

- **Core DataKey**：仅在 `data_types/data_keys.py` 维护框架白名单；**升级会覆盖，用户勿改此文件**。
- **Userspace DataKey**：在用户目录用稳定字符串定义（见 `userspace.data_contract` 与 `userspace_contract_discovery`），通过发现机制与 core 合并。
- **定义如何签发**：`ContractRouteRegistry.register`；或由 `DataContractManager` 使用默认合并表（core + userspace 发现）。

工厂签名：`factory(key_str, context) -> BaseContract`，其中 `key_str` 与 DataKey.value 一致，用于 contract_id/name。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Tuple, Union

from core.modules.data_contract.contracts import (
    BaseContract,
    GlobalNoTimeAxisContract,
    GlobalTimeAxisContract,
    PerEntityNoTimeAxisContract,
    PerEntityTimeAxisContract,
)
from core.modules.data_contract.data_types import DataKey

TAG_KIND_CONTEXT_KEY = "tag_kind"

_DEFAULT_TAG_KIND = "eventlog"

_KLINE_REQUIRED: Tuple[str, ...] = ("open", "high", "low", "close")

ContractFactory = Callable[[str, Optional[Mapping[str, Any]]], BaseContract]


def _as_key_str(key: Union[DataKey, str]) -> str:
    return key.value if isinstance(key, DataKey) else key


def _pe_time_axis(
    key_str: str,
    *,
    time_axis_field: str,
    required_fields: Tuple[str, ...] = (),
) -> PerEntityTimeAxisContract:
    return PerEntityTimeAxisContract(
        contract_id=key_str,
        name=key_str,
        time_axis_field=time_axis_field,
        required_fields=required_fields,
    )


def _global_time_axis(
    key_str: str,
    *,
    time_axis_field: str,
    required_fields: Tuple[str, ...] = (),
) -> GlobalTimeAxisContract:
    return GlobalTimeAxisContract(
        contract_id=key_str,
        name=key_str,
        time_axis_field=time_axis_field,
        required_fields=required_fields,
    )


def _global_no_time_axis(key_str: str) -> GlobalNoTimeAxisContract:
    return GlobalNoTimeAxisContract(contract_id=key_str, name=key_str)


def _tag_scenario_factory(key_str: str, context: Optional[Mapping[str, Any]]) -> BaseContract:
    ctx = dict(context or {})
    kind = ctx.get(TAG_KIND_CONTEXT_KEY) or _DEFAULT_TAG_KIND
    if isinstance(kind, str):
        kind = kind.lower()
    else:
        kind = str(kind).lower()

    if kind == "category":
        return PerEntityNoTimeAxisContract(contract_id=key_str, name=key_str)

    return PerEntityTimeAxisContract(
        contract_id=key_str,
        name=key_str,
        time_axis_field="as_of_date",
        required_fields=(),
    )


class ContractRouteRegistry:
    """
    key_str（= DataKey.value）到 Contract 工厂的映射。线程安全不保证；通常在进程启动时构建。
    """

    __slots__ = ("_routes",)

    def __init__(self, routes: Optional[Dict[str, ContractFactory]] = None) -> None:
        self._routes: Dict[str, ContractFactory] = dict(routes or {})

    def register(self, key: Union[DataKey, str], factory: ContractFactory) -> None:
        ks = _as_key_str(key)
        self._routes[ks] = factory

    def merge(self, other: ContractRouteRegistry, *, other_wins: bool = True) -> ContractRouteRegistry:
        if other_wins:
            merged = dict(self._routes)
            merged.update(other._routes)
        else:
            merged = dict(other._routes)
            merged.update(self._routes)
        return ContractRouteRegistry(merged)

    def resolve(self, key: Union[DataKey, str], context: Optional[Mapping[str, Any]] = None) -> BaseContract:
        ks = _as_key_str(key)
        factory = self._routes.get(ks)
        if factory is None:
            raise KeyError(f"ContractRouteRegistry: no factory registered for key={ks!r}")
        return factory(ks, context)

    def has(self, key: Union[DataKey, str]) -> bool:
        return _as_key_str(key) in self._routes


def build_core_contract_route_registry() -> ContractRouteRegistry:
    """框架内置：与当前 `DataKey` 白名单一致的默认路由。"""
    reg = ContractRouteRegistry()

    reg.register(DataKey.STOCK_KLINE_DAILY_QFQ, lambda k, ctx: _pe_time_axis(k, time_axis_field="date", required_fields=_KLINE_REQUIRED))
    reg.register(DataKey.STOCK_KLINE_DAILY_NFQ, lambda k, ctx: _pe_time_axis(k, time_axis_field="date", required_fields=_KLINE_REQUIRED))
    reg.register(DataKey.STOCK_ADJ_FACTOR_EVENTS, lambda k, ctx: _pe_time_axis(k, time_axis_field="event_date", required_fields=()))
    reg.register(DataKey.STOCK_CORPORATE_FINANCE, lambda k, ctx: _pe_time_axis(k, time_axis_field="quarter", required_fields=()))

    reg.register(DataKey.INDEX_KLINE_DAILY, lambda k, ctx: _pe_time_axis(k, time_axis_field="date", required_fields=_KLINE_REQUIRED))
    reg.register(DataKey.INDEX_WEIGHT_DAILY, lambda k, ctx: _pe_time_axis(k, time_axis_field="date", required_fields=()))
    reg.register(DataKey.INDEX_LIST, lambda k, ctx: _global_no_time_axis(k))

    reg.register(DataKey.MACRO_GDP, lambda k, ctx: _global_time_axis(k, time_axis_field="quarter", required_fields=()))
    for macro in (
        DataKey.MACRO_LPR,
        DataKey.MACRO_CPI,
        DataKey.MACRO_PPI,
        DataKey.MACRO_PMI,
        DataKey.MACRO_SHIBOR,
        DataKey.MACRO_MONEY_SUPPLY,
    ):
        reg.register(macro, lambda k, ctx: _global_time_axis(k, time_axis_field="date", required_fields=()))

    for static in (
        DataKey.STOCK_LIST,
        DataKey.STOCK_INDUSTRIES,
        DataKey.STOCK_BOARDS,
        DataKey.STOCK_MARKETS,
        DataKey.STOCK_INDUSTRY_MAP,
        DataKey.STOCK_BOARD_MAP,
        DataKey.STOCK_MARKET_MAP,
        DataKey.SYSTEM_META_INFO,
        DataKey.SYSTEM_CACHE,
    ):
        reg.register(static, lambda k, ctx: _global_no_time_axis(k))

    reg.register(DataKey.TAG_SCENARIO, _tag_scenario_factory)

    return reg
