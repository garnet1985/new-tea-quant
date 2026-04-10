from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.contract_issuer import ContractIssuer
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.discovery import discover_userspace_map
from core.modules.data_contract.mapping import DataSpecMap, default_map


class DataContractManager:
    """Manager: discover/merge map, expose unified issue API."""

    def __init__(self) -> None:
        custom_map = self._discover_custom_map()
        self.map: DataSpecMap = self._merge_map(default_map, custom_map)
        self.issuer = ContractIssuer(self.map)

    def issue(
        self,
        data_id: DataKey,
        *,
        context: Optional[Mapping[str, Any]] = None,
        **override_params: Any,
    ) -> DataContract:
        return self.issuer.issue(data_id, context=context, **override_params)

    def _discover_custom_map(self) -> DataSpecMap:
        return discover_userspace_map()

    def _merge_map(self, base_map: DataSpecMap, custom_map: DataSpecMap) -> DataSpecMap:
        merged: DataSpecMap = dict(base_map)
        for data_id, spec in custom_map.items():
            if data_id in merged:
                raise ValueError(f"发现重复 data_id 注册：{data_id.value}")
            merged[data_id] = spec
        return merged
