"""Userspace 规则类工厂发现与 core 路由合并。"""

from core.modules.data_contract.discovery.userspace import (
    USERSPACE_DATA_CONTRACT_PACKAGE,
    build_merged_contract_route_registry,
    default_contract_route_registry,
    load_userspace_contract_route_registry,
)

__all__ = [
    "USERSPACE_DATA_CONTRACT_PACKAGE",
    "build_merged_contract_route_registry",
    "default_contract_route_registry",
    "load_userspace_contract_route_registry",
]
