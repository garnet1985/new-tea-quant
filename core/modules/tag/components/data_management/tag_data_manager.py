from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_cursor import DataCursorManager
from core.utils.date.date_utils import DateUtils

if TYPE_CHECKING:
    from core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)

class TagDataManager:
    """Tag 子进程数据管理：契约签发、装填、游标切片。"""

    def __init__(
        self,
        *,
        entity_id: str,
        entity_type: str,
        scenario_name: str,
        settings: Dict[str, Any],
        data_mgr: "DataManager",
        contract_cache: ContractCacheManager,
        global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.scenario_name = scenario_name
        self.settings = settings
        self.data_mgr = data_mgr
        self._contract_cache = contract_cache
        self._global_extra_cache = global_extra_cache or {}

        self._dcf_mgr: Optional[DataContractManager] = None
        self._current_data: Dict[str, List[Dict[str, Any]]] = {}
        self._slot_contracts: Dict[str, DataContract] = {}
        self._cursor_mgr = DataCursorManager()
        self._cursor_name = f"tag:{self.scenario_name}:{self.entity_id}"
        self._axis_data_id: Optional[DataKey] = None

    def _contract_manager(self) -> DataContractManager:
        if self._dcf_mgr is None:
            self._dcf_mgr = DataContractManager(contract_cache=self._contract_cache)
        return self._dcf_mgr

    def issue_contracts(
        self,
        *,
        start: str,
        end: str,
        entity_id: Optional[str] = None,
        data_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[DataKey, DataContract]:
        block = data_block if data_block is not None else self.settings.get("data", {})
        declarations = list(block.get("required") or [])

        eff_entity = entity_id.strip() if entity_id and str(entity_id).strip() else None
        out: Dict[DataKey, DataContract] = {}
        dcm = self._contract_manager()
        for raw in declarations:
            item = self._normalize_declaration_item(raw)
            dk = DataKey(str(item["data_id"]))
            params = dict(item.get("params") or {})
            spec = dcm.map.get(dk)
            if spec is None:
                raise ValueError(f"未注册的 data_id：{dk.value}")
            if spec.get("scope") == ContractScope.PER_ENTITY and eff_entity is None:
                raise ValueError(f"{dk.value} 需要 entity_id，但当前未提供")

            ent = eff_entity if spec.get("scope") == ContractScope.PER_ENTITY else None
            contract = dcm.issue(
                dk,
                entity_id=ent,
                start=start,
                end=end,
                **params,
            )
            if dk in out:
                raise ValueError(
                    f"data 声明中重复的 data_id：{dk.value!r}（dict 存储下无法同时保留两条）"
                )
            out[dk] = contract
        axis = self._resolve_axis_data_id(block=block, declarations=declarations)
        if axis is not None:
            self._axis_data_id = DataKey(axis)
        return out

    def _normalize_declaration_item(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(raw)
        dk = DataKey(str(item["data_id"]))
        params = dict(item.get("params") or {})
        if dk == DataKey.TAG:
            if str(params.get("scenario_name") or "").strip() == "":
                params["scenario_name"] = self.scenario_name
            if str(params.get("entity_type") or "").strip() == "":
                params["entity_type"] = self.entity_type
            item["params"] = params
        return item

    def hydrate_row_slots(self, start_date: str, end_date: str) -> None:
        self._contract_cache.enter_strategy_run()
        self._slot_contracts = {}
        self._current_data = {}
        contracts = self.issue_contracts(
            start=start_date,
            end=end_date,
            entity_id=self.entity_id,
        )
        dcm = self._contract_manager()
        for dk, contract in contracts.items():
            spec = dcm.map.get(dk)
            slot = dk.value
            if (
                spec
                and spec.get("scope") == ContractScope.GLOBAL
                and slot in self._global_extra_cache
            ):
                rows = list(self._global_extra_cache[slot] or [])
                contract.data = rows
            else:
                if contract.needs_load:
                    contract.load(start=start_date, end=end_date)
                rows = list(contract.data or [])
            self._current_data[slot] = rows
            self._slot_contracts[slot] = contract

    def rebuild_data_cursor(self) -> None:
        if not self._slot_contracts:
            raise ValueError("当前无可用 contract，无法构建 DataCursor")
        self._cursor_mgr.create_cursor(self._cursor_name, contracts=self._slot_contracts)

    def get_loaded_data(self) -> Dict[str, Any]:
        return self._adapt_worker_data(self._current_data)

    def get_data_until(self, as_of_date: str) -> Dict[str, Any]:
        cursor = self._cursor_mgr.get_cursor(self._cursor_name)
        sliced = cursor.until(as_of_date)
        return self._adapt_worker_data(sliced)

    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        axis_key = self._axis_data_id
        if axis_key is None:
            axis_key = DataKey.STOCK_KLINE
        axis_slot = axis_key.value
        rows = self._current_data.get(axis_slot) or []
        if not rows:
            return []
        contract = self._slot_contracts.get(axis_slot)
        time_field = "date"
        if contract and contract.meta and isinstance(contract.meta.attrs, dict):
            time_field = str(contract.meta.attrs.get("time_axis_field") or "date")

        all_dates = sorted(
            {
                DateUtils.normalize(r.get(time_field), fmt=DateUtils.FMT_YYYYMMDD)
                for r in rows
                if r.get(time_field)
            }
        )
        all_dates = [d for d in all_dates if d]
        if not all_dates:
            return []

        left = start_date or all_dates[0]
        right = end_date or all_dates[-1]
        max_date = all_dates[-1]
        if right and max_date and right > max_date:
            right = max_date
        return [d for d in all_dates if left <= d <= right]

    def _resolve_axis_data_id(self, *, block: Dict[str, Any], declarations: List[Dict[str, Any]]) -> Optional[str]:
        configured = str(block.get("tag_time_axis_based_on") or "").strip()
        if configured:
            return configured

        # 默认主轴：使用 required 中第一个 PER_ENTITY 合约（source of truth 来自 contract map）
        dcm = self._contract_manager()
        for item in declarations:
            raw = str(item.get("data_id") or "").strip()
            if not raw:
                continue
            try:
                dk = DataKey(raw)
            except ValueError:
                continue
            spec = dcm.map.get(dk)
            if spec and spec.get("scope") == ContractScope.PER_ENTITY:
                return dk.value

        if declarations:
            return str(declarations[0].get("data_id") or "").strip() or None
        return None

    def _adapt_worker_data(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        return {k: list(v or []) for k, v in data.items()}
