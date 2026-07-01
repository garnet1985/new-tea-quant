"""DataContracts facade — public entry for issue / load pipeline."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from core.modules.data_contract.core.cache import ContractCacheManager
from core.modules.data_contract.core.contract.data_class.issue_result import IssueResult
from core.modules.data_contract.core.issue.manager import DataContractManager
from core.modules.data_contract.core.registry.contract_const import DataKey
from core.modules.data_contract.core.registry.mapping import DataSpecMap


class DataContracts:
    """Data contract facade: discover map, issue handles, coordinate cache."""

    def __init__(self, *, contract_cache: ContractCacheManager) -> None:
        self._manager = DataContractManager(contract_cache=contract_cache)

    @property
    def map(self) -> DataSpecMap:
        return self._manager.map

    def issue(
        self,
        data_id: DataKey,
        *,
        entity_id: Optional[str] = None,
        entity_ids: Optional[Sequence[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **override_params: Any,
    ) -> IssueResult:
        return self._manager.issue(
            data_id,
            entity_id=entity_id,
            entity_ids=entity_ids,
            start=start,
            end=end,
            **override_params,
        )
