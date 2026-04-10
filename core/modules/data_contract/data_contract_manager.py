#!/usr/bin/env python3
"""
Data Contract Manager

职责（MVP）：
- 编排入口：解析 contract 并对 raw 执行 `issue`（fail-closed）。
- **默认**加载 **core 白名单路由 + userspace 发现的路由** 并合并（见 `userspace_contract_discovery`），供策略与其它模块**同一注入点**使用。
- 传入自定义 `registry` 时可跳过默认合并（测试或完全自控）。

非职责（MVP）：
- 不负责 query / join / DataManager 的加载逻辑（raw data 由上游提供）
- 不负责落库/导入

Userspace：
- 用户**不得**修改 core 的 `data_keys.py`（升级会丢）；在 `userspace.data_contract` 下注册 `register_data_contract_routes`。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from core.modules.data_contract.contracts import BaseContract
from core.modules.data_contract.contract_route_registry import (
    TAG_KIND_CONTEXT_KEY,
    ContractRouteRegistry,
    build_core_contract_route_registry,
)
from core.modules.data_contract.data_types import DataKey
from core.modules.data_contract.userspace_contract_discovery import default_contract_route_registry


class DataContractManager:
    """
    持有合并后的 `ContractRouteRegistry` 并转发 `resolve_contract` / `issue`。
    """

    __slots__ = ("_registry",)

    def __init__(
        self,
        registry: Optional[ContractRouteRegistry] = None,
        *,
        merge_userspace: bool = True,
    ) -> None:
        if registry is not None:
            self._registry = registry
        elif merge_userspace:
            self._registry = default_contract_route_registry()
        else:
            self._registry = build_core_contract_route_registry()

    def issue(
        self,
        key: Union[DataKey, str],
        raw: Any,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        contract = self.resolve_contract(key, context=context)
        return contract.issue(raw, context=context)

    def resolve_contract(
        self,
        key: Union[DataKey, str],
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> BaseContract:
        return self._registry.resolve(key, context)
