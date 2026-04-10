"""
Data Contract module.

This module is the issuer/manager of data contracts.
It defines how raw/untrusted data is validated and normalized into
contracted (trusted) data for the rest of the application.
"""

from core.modules.data_contract.contract_route_registry import (
    ContractRouteRegistry,
    build_core_contract_route_registry,
)
from core.modules.data_contract.data_contract_manager import DataContractManager, TAG_KIND_CONTEXT_KEY
from core.modules.data_contract.data_types import DataKey
from core.modules.data_contract.userspace_contract_discovery import (
    USERSPACE_DATA_CONTRACT_PACKAGE,
    build_merged_contract_route_registry,
    default_contract_route_registry,
    load_userspace_contract_route_registry,
)

__all__ = [
    "DataContractManager",
    "DataKey",
    "TAG_KIND_CONTEXT_KEY",
    "ContractRouteRegistry",
    "build_core_contract_route_registry",
    "build_merged_contract_route_registry",
    "default_contract_route_registry",
    "load_userspace_contract_route_registry",
    "USERSPACE_DATA_CONTRACT_PACKAGE",
]
