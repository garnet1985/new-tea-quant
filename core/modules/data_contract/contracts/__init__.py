"""
Contracts package.

MVP: framework-internal contracts (not user-extensible).
"""

from .base import BaseContract, ContractScope, GlobalContract, PerEntityContract
from .global_time_axis import GlobalTimeAxisContract
from .global_non_time_axis import GlobalNoTimeAxisContract, StaticCategoryContract
from .per_entity_non_time_axis import PerEntityNoTimeAxisContract, PerEntityStaticCategoryContract
from .per_entity_time_axis import PerEntityTimeAxisContract

__all__ = [
    "BaseContract",
    "ContractScope",
    "GlobalContract",
    "GlobalTimeAxisContract",
    "GlobalNoTimeAxisContract",
    "PerEntityContract",
    "PerEntityNoTimeAxisContract",
    "PerEntityStaticCategoryContract",
    "PerEntityTimeAxisContract",
    "StaticCategoryContract",
]

