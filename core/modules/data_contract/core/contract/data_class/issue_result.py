from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from core.modules.data_contract.core.registry.contract_const import ContractScope, DataKey
from core.modules.data_contract.core.contract.contracts import DataContract


@dataclass(frozen=True)
class IssueResult:
    """``issue`` 的统一返回信封（见 ``docs/DECISIONS.md`` 决策 8–9）。"""

    data_id: DataKey
    scope: ContractScope
    contract: Optional[DataContract] = None
    by_entity: Optional[Mapping[str, DataContract]] = None

    @property
    def entity_count(self) -> int:
        if self.by_entity is None:
            return 0
        return len(self.by_entity)

    def entity(self, entity_id: str) -> DataContract:
        if self.by_entity is None:
            raise ValueError(
                f"data_id={self.data_id.value} 为 GLOBAL，无 by_entity；请使用 contract"
            )
        key = str(entity_id).strip()
        if not key or key not in self.by_entity:
            raise KeyError(f"entity_id={entity_id!r} 不在 issue 结果中")
        return self.by_entity[key]

    def require_one(self) -> DataContract:
        if self.by_entity is None:
            raise ValueError(
                f"data_id={self.data_id.value} 为 GLOBAL，无 by_entity；请使用 contract"
            )
        if len(self.by_entity) != 1:
            raise ValueError(
                f"PER_ENTITY issue 含 {len(self.by_entity)} 个 entity，无法 require_one()"
            )
        return next(iter(self.by_entity.values()))

    def require_contract(self, *, entity_id: Optional[str] = None) -> DataContract:
        """GLOBAL 返回 ``contract``；PER_ENTITY 返回指定或唯一 entity 的句柄。"""
        if self.contract is not None:
            if entity_id is not None:
                raise ValueError("GLOBAL issue 不应指定 entity_id")
            return self.contract
        if self.by_entity is not None:
            if entity_id is not None:
                return self.entity(entity_id)
            return self.require_one()
        raise ValueError(f"空的 IssueResult：data_id={self.data_id.value}")
