"""
Base building blocks for contracts.

Keep foundational abstractions here to avoid clutter in contracts root.
"""

from .contract_scope import ContractScope
from .base import BaseContract
from .global_base import GlobalContract
from .per_entity_base import PerEntityContract

__all__ = [
    "ContractScope",
    "BaseContract",
    "GlobalContract",
    "PerEntityContract",
]

