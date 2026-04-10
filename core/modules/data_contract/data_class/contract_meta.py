from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.modules.data_contract.contract_const import ContractScope, DataKey


@dataclass
class ContractMeta:
    """Frozen shape/meta for an issued contract handle."""

    data_id: DataKey
    name: str
    scope: ContractScope
    display_name: str = ""
    attrs: Mapping[str, Any] = field(default_factory=dict)
