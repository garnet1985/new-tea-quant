"""
路由注册表与 `DataContractManager`（当前以 **规则类 + 校验 raw** 为主路径）。

句柄 `issue` / `DataEntity` / resolver 见 `runtime/` 与 `CONCEPTS.md`。

导入顺序：`route_registry` 必须在 `manager` 之前，避免 `discovery.userspace` ↔ `registry` 循环依赖。
"""

from core.modules.data_contract.registry.route_registry import (
    TAG_KIND_CONTEXT_KEY,
    ContractRouteRegistry,
    build_core_contract_route_registry,
)
from core.modules.data_contract.registry.manager import DataContractManager

__all__ = [
    "DataContractManager",
    "TAG_KIND_CONTEXT_KEY",
    "ContractRouteRegistry",
    "build_core_contract_route_registry",
]
