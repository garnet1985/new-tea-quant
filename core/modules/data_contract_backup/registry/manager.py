#!/usr/bin/env python3
"""
Data Contract Manager

**命名说明（易混）**：见包内 `CONCEPTS.md` 与 `runtime/pipeline.py`。

- **`validate_raw(key, raw)`**：选用规则类并对 **裸数据** 校验（委托规则类 `validate_raw`）。
- **`issue_handle(key, params, context)`**：句柄语义 —— 得到 **已定稿、数据仍空** 的 `DataEntity`（不拉数）。

职责：
- 持有 `ContractRouteRegistry`（默认 core + userspace 合并）。
- 提供 **句柄 issue**、**raw 校验** 两条入口。

非职责：
- 不在本类内调用 DataManager；物化由 `DataEntity.load` + 已注册的 resolver 完成。

Userspace：在 `userspace.data_contract` 注册规则类工厂；勿改 core `ids/data_keys.py`。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from core.modules.data_contract.contracts import BaseContract
from core.modules.data_contract.ids import DataKey
from core.modules.data_contract.registry.route_registry import ContractRouteRegistry, build_core_contract_route_registry
from core.modules.data_contract.runtime.contract_meta import build_rule_meta
from core.modules.data_contract.runtime.data_entity import DataEntity


class DataContractManager:
    """
    持有合并后的 `ContractRouteRegistry`。

    - `issue_handle`：句柄 **issue** → `DataEntity`（meta 来自规则类快照，数据匣空）。
    - `validate_raw`：**校验 raw**（规则类 `validate_raw`）。
    - `resolve_contract`：仅得到 **规则类实例**。
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
            from core.modules.data_contract.discovery.userspace import default_contract_route_registry

            self._registry = default_contract_route_registry()
        else:
            self._registry = build_core_contract_route_registry()

    def issue_handle(
        self,
        key: Union[DataKey, str],
        *,
        params: Optional[Mapping[str, Any]] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> DataEntity:
        """
        句柄 issue：解析路由 → 规则类 → 固化 **meta**；**不**读取或填充大数据主体。

        `context` 参与路由（如 `TAG_SCENARIO` 的 tag_kind）；`params` 为策略侧覆盖参数（浅合并由调用方或 `merge_params` 处理）。
        """
        ks = key.value if isinstance(key, DataKey) else key
        contract = self.resolve_contract(key, context=context)
        meta = build_rule_meta(contract)
        return DataEntity(data_id=ks, params=dict(params or {}), meta=meta)

    def validate_raw(
        self,
        key: Union[DataKey, str],
        raw: Any,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """解析 key → 规则类 → `validate_raw(raw)`（fail-closed）。"""
        contract = self.resolve_contract(key, context=context)
        return contract.validate_raw(raw, context=context)

    def resolve_contract(
        self,
        key: Union[DataKey, str],
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> BaseContract:
        return self._registry.resolve(key, context)
