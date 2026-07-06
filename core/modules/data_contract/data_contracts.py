"""DataContracts facade — public entry for issue / load pipeline."""
from __future__ import annotations

from typing import Any, Hashable, Mapping, Optional, Sequence

from core.modules.data_contract.core.cache.default_store import shared_contract_cache
from core.modules.data_contract.core.cache.contract_cache_manager import ContractCacheManager
from core.modules.data_contract.core.contract.contracts import DataContract
from core.modules.data_contract.core.contract.data_class.contract_info import (
    ContractInfo,
    TimeRange,
    UntilResult,
)
from core.modules.data_contract.core.contract.data_class.issue_result import IssueResult
from core.modules.data_contract.core.facade.time_helpers import ContractTimeHelper
from core.modules.data_contract.core.issue.manager import DataContractManager
from core.modules.data_contract.core.registry.contract_const import DataKey
from core.modules.data_cursor import DataCursorManager


class DataContract:
    """Data contract facade: info, issue, load, until; cache black-box for GLOBAL only."""

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
        data: Any = None,
        data_by_entity: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
        **override_params: Any,
    ) -> IssueResult:
        return self._manager.issue(
            data_id,
            entity_id=entity_id,
            entity_ids=entity_ids,
            start=start,
            end=end,
            should_load_initially=should_load_initially,
            data=data,
            data_by_entity=data_by_entity,
            **override_params,
        )

    def load(self, issued: IssueResult) -> IssueResult:
        return self._manager.load(issued)

    def open_until_cursor(
        self,
        name: str,
        contracts: Mapping[Hashable, DataContract],
    ) -> None:
        """Bind a multi-source until session (hot path — delegates to DataCursor)."""
        for contract in contracts.values():
            ContractTimeHelper.require_loaded(contract)
        self._cursor_mgr.create_cursor(name, contracts=contracts)

    def until_cursor(self, name: str, as_of: str) -> dict[Hashable, list[dict[str, Any]]]:
        """Advance named until session to as_of; returns cumulative prefix view per source."""
        return self._cursor_mgr.get_cursor(name).until(as_of)

    def reset_until_cursor_session(self, name: str) -> None:
        """Reset scan state for a named multi-source until session."""
        self._cursor_mgr.reset_cursor(name)

    def close_until_cursor(self, name: str) -> None:
        """Drop a named multi-source until session."""
        self._cursor_mgr.drop_cursor(name)

    def until(
        self,
        contract: DataContract,
        as_of: str,
        *,
        reset: bool = False,
    ) -> UntilResult:
        """Single-contract until sugar; execute loops prefer open_until_cursor + until_cursor."""
        ContractTimeHelper.require_loaded(contract)
        if reset:
            self.reset_until_cursor(contract)

        from core.modules.data_cursor import DataCursor

        cursor = self._until_cursors.get(id(contract))
        if cursor is None:
            key = contract.meta.key
            cursor = DataCursor(contracts={key: contract})
            self._until_cursors[id(contract)] = cursor

        as_of_norm = ContractTimeHelper.normalize_as_of(contract, as_of)
        rows = cursor.until(as_of)[contract.meta.key]
        return UntilResult(rows=rows, as_of=as_of_norm)

    def reset_until_cursor(self, contract: DataContract) -> None:
        """Drop cached until-cursor state for this contract handle."""
        self._until_cursors.pop(id(contract), None)

    def get_data_window(self, contract: DataContract) -> Optional[TimeRange]:
        return ContractTimeHelper.user_data_window(contract)

    def get_data_window_edge(self, contract: DataContract) -> Optional[TimeRange]:
        return ContractTimeHelper.data_window_edge(contract)

    def get_start_time(self, contract: DataContract) -> Optional[str]:
        return ContractTimeHelper.user_start(contract)

    def get_end_time(self, contract: DataContract) -> Optional[str]:
        return ContractTimeHelper.user_end(contract)

    def get_data_edge_start(self, contract: DataContract) -> Optional[str]:
        return ContractTimeHelper.data_edge_start(contract)

    def get_data_edge_end(self, contract: DataContract) -> Optional[str]:
        return ContractTimeHelper.data_edge_end(contract)

    def is_loaded(self, contract: DataContract) -> bool:
        return contract.data is not None

    def row_count(self, contract: DataContract) -> int:
        ContractTimeHelper.require_loaded(contract)
        if isinstance(contract.data, list):
            return len(contract.data)
        raise ValueError(f"contract={contract.meta.data_id.value} 的 data 不是 list")

    @staticmethod
    def shared_cache() -> ContractCacheManager:
        """run 边界 enter/exit_strategy_run；高级场景访问同一 store。"""
        return shared_contract_cache()

    @staticmethod
    def get_spec(data_key: DataKey) -> Optional[Mapping[str, Any]]:
        """通过 DataKey 获取 spec（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            spec 字典（包含 scope、type、loader、storage 等），如果不存在返回 None

        示例：
            spec = DataContracts.get_spec(DataKey.STOCK_KLINE_DAILY)
            if spec:
                scope = spec.get("scope")  # ContractScope.PER_ENTITY
                type = spec.get("type")    # ContractType.TIME_SERIES
        """
        from core.modules.data_contract.core.registry.mapping import default_map
        
        dk = data_key if isinstance(data_key, DataKey) else DataKey(str(data_key).strip())
        return default_map.get(dk)

    @staticmethod
    def get_scope(data_key: DataKey) -> Optional[str]:
        """通过 DataKey 获取 scope（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            scope 字符串（"global" 或 "per_entity"），如果不存在返回 None

        示例：
            scope = DataContracts.get_scope(DataKey.STOCK_KLINE_DAILY)
            # 返回 "per_entity"
        """
        spec = DataContracts.get_spec(data_key)
        if spec is None:
            return None
        
        from core.modules.data_contract.core.registry.contract_const import ContractScope
        
        scope = spec.get("scope")
        if scope == ContractScope.GLOBAL:
            return "global"
        elif scope == ContractScope.PER_ENTITY:
            return "per_entity"
        else:
            return str(scope) if scope else None

    @staticmethod
    def get_type(data_key: DataKey) -> Optional[str]:
        """通过 DataKey 获取 type（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            type 字符串（"time_series" 或 "non_time_series"），如果不存在返回 None

        示例：
            type = DataContracts.get_type(DataKey.STOCK_KLINE_DAILY)
            # 返回 "time_series"
        """
        spec = DataContracts.get_spec(data_key)
        if spec is None:
            return None
        
        from core.modules.data_contract.core.registry.contract_const import ContractType
        
        type = spec.get("type")
        if type == ContractType.TIME_SERIES:
            return "time_series"
        elif type == ContractType.NON_TIME_SERIES:
            return "non_time_series"
        else:
            return str(type) if type else None

    @staticmethod
    def is_global(data_key: DataKey) -> bool:
        """判断 DataKey 是否为 GLOBAL scope（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            True 如果 scope 为 GLOBAL，否则 False

        示例：
            if DataContracts.is_global(DataKey.MACRO_GDP):
                # 处理全局数据
        """
        scope = DataContracts.get_scope(data_key)
        return scope == "global"

    @staticmethod
    def is_per_entity(data_key: DataKey) -> bool:
        """判断 DataKey 是否为 PER_ENTITY scope（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            True 如果 scope 为 PER_ENTITY，否则 False

        示例：
            if DataContracts.is_per_entity(DataKey.STOCK_KLINE_DAILY):
                # 处理 per_entity 数据
        """
        scope = DataContracts.get_scope(data_key)
        return scope == "per_entity"

    @staticmethod
    def is_time_series(data_key: DataKey) -> bool:
        """判断 DataKey 是否为 TIME_SERIES type（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            True 如果 type 为 TIME_SERIES，否则 False

        示例：
            if DataContracts.is_time_series(DataKey.STOCK_KLINE_DAILY):
                # 处理时序数据
        """
        type = DataContracts.get_type(data_key)
        return type == "time_series"

    @staticmethod
    def is_non_time_series(data_key: DataKey) -> bool:
        """判断 DataKey 是否为 NON_TIME_SERIES type（静态方法）。

        Args:
            data_key: DataKey 实例或字符串

        Returns:
            True 如果 type 为 NON_TIME_SERIES，否则 False

        示例：
            if DataContracts.is_non_time_series(DataKey.STOCK_LIST):
                # 处理非时序数据
        """
        type = DataContracts.get_type(data_key)
        return type == "non_time_series"


__all__ = ["DataContract"]