"""
Data Contract module.

**术语与目标架构（必读）**：`CONCEPTS.md`；**主链路步骤**见 `runtime/pipeline.py` 文档字符串。

- **句柄**：`DataContractManager.issue_handle` → `DataEntity` → `DataEntity.load`（`ResolverRegistry`）。
- **校验 raw**：`DataContractManager.validate_raw` → 规则类 **`validate_raw(raw)`**。
"""

from core.modules.data_contract.discovery import (
    USERSPACE_DATA_CONTRACT_PACKAGE,
    build_merged_contract_route_registry,
    default_contract_route_registry,
    load_userspace_contract_route_registry,
)
from core.modules.data_contract.ids import DataKey
from core.modules.data_contract.registry import (
    TAG_KIND_CONTEXT_KEY,
    ContractRouteRegistry,
    DataContractManager,
    build_core_contract_route_registry,
)
from core.modules.data_contract.runtime import DataEntity, ResolverRegistry, build_rule_meta, merge_params

__all__ = [
    "DataContractManager",
    "DataEntity",
    "DataKey",
    "ResolverRegistry",
    "TAG_KIND_CONTEXT_KEY",
    "ContractRouteRegistry",
    "build_core_contract_route_registry",
    "build_merged_contract_route_registry",
    "build_rule_meta",
    "default_contract_route_registry",
    "load_userspace_contract_route_registry",
    "merge_params",
    "USERSPACE_DATA_CONTRACT_PACKAGE",
]
