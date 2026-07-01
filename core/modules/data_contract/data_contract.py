"""DataContracts facade — public entry for issue / load pipeline."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from core.modules.data_contract.core.cache.default_store import shared_contract_cache
from core.modules.data_contract.core.cache.contract_cache_manager import ContractCacheManager
from core.modules.data_contract.core.contract.contracts import DataContract
from core.modules.data_contract.core.contract.data_class.contract_info import (
    ContractInfo,
    TimeRange,
    UntilResult,
)
from core.modules.data_contract.core.contract.data_class.issue_result import IssueResult
from core.modules.data_contract.core.facade import time_helpers
from core.modules.data_contract.core.issue.manager import DataContractManager
from core.modules.data_contract.core.registry.contract_const import DataKey
from core.utils.date.date_utils import DateUtils


class DataContracts:
    """Data contract facade: info, issue, load, until; cache black-box for GLOBAL only."""

    def __init__(self, *, cache_enabled: bool = True) -> None:
        cache = shared_contract_cache()
        self._cache_enabled = cache_enabled
        self._manager = DataContractManager(
            contract_cache=cache,
            cache_enabled=cache_enabled,
        )
        self._until_cursors: dict[int, Any] = {}

    @property
    def map(self):
        return self._manager.map

    def info(self, data_key: DataKey) -> ContractInfo:
        return self._manager.info(data_key)

    def issue(
        self,
        data_id: DataKey,
        *,
        entity_id: Optional[str] = None,
        entity_ids: Optional[Sequence[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        should_load_initially: bool = True,
        **override_params: Any,
    ) -> IssueResult:
        return self._manager.issue(
            data_id,
            entity_id=entity_id,
            entity_ids=entity_ids,
            start=start,
            end=end,
            should_load_initially=should_load_initially,
            **override_params,
        )

    def load(self, issued: IssueResult) -> IssueResult:
        return self._manager.load(issued)

    def until(
        self,
        contract: DataContract,
        as_of: str,
        *,
        reset: bool = False,
    ) -> UntilResult:
        time_helpers.require_loaded(contract)
        if reset:
            self._until_cursors.pop(id(contract), None)

        from core.modules.data_cursor import DataCursor

        cursor = self._until_cursors.get(id(contract))
        if cursor is None:
            key = contract.meta.data_id
            cursor = DataCursor(contracts={key: contract})
            self._until_cursors[id(contract)] = cursor

        as_of_norm = DateUtils.normalize(as_of, fmt=DateUtils.FMT_YYYYMMDD)
        if as_of_norm is None:
            fmt = time_helpers.time_axis_format(contract)
            as_of_norm = DateUtils.normalize(as_of, fmt=fmt) if fmt else None
        if as_of_norm is None:
            raise ValueError(f"as_of 格式非法：{as_of!r}")

        rows = list(cursor.until(as_of)[contract.meta.data_id])
        return UntilResult(rows=rows, as_of=as_of_norm)

    def get_data_window(self, contract: DataContract) -> Optional[TimeRange]:
        return time_helpers.user_data_window(contract)

    def get_data_window_edge(self, contract: DataContract) -> Optional[TimeRange]:
        return time_helpers.data_window_edge(contract)

    def get_start_time(self, contract: DataContract) -> Optional[str]:
        return time_helpers.user_start(contract)

    def get_end_time(self, contract: DataContract) -> Optional[str]:
        return time_helpers.user_end(contract)

    def get_data_edge_start(self, contract: DataContract) -> Optional[str]:
        return time_helpers.data_edge_start(contract)

    def get_data_edge_end(self, contract: DataContract) -> Optional[str]:
        return time_helpers.data_edge_end(contract)

    def is_loaded(self, contract: DataContract) -> bool:
        return contract.data is not None

    def row_count(self, contract: DataContract) -> int:
        time_helpers.require_loaded(contract)
        if isinstance(contract.data, list):
            return len(contract.data)
        raise ValueError(f"contract={contract.meta.data_id.value} 的 data 不是 list")

    @staticmethod
    def shared_cache() -> ContractCacheManager:
        """run 边界 enter/exit_strategy_run；高级场景访问同一 store。"""
        return shared_contract_cache()
